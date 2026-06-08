"""
Cocotb testbench for rrfifo_async — dual-clock (asynchronous) FIFO.

The write and read interfaces run on independent clocks (deliberately different
periods so the clock-domain crossing is genuinely exercised). Because pointers
take SYNC_STAGES destination cycles to cross domains, the helpers below wait on
full_o / empty_o rather than assuming instantaneous flag updates.

WR_MODE / RD_MODE are compile-time SV string parameters ("LEVEL" or "PULSE").
The Makefile exports the elaborated value into the environment so this test can
pick the matching expectations. The per-word write/read helpers pulse the enable
for exactly one cycle, so they behave identically under both modes — only the
dedicated "held-high" tests below distinguish LEVEL from PULSE.
"""

import collections
import os
import random
import traceback

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge, with_timeout
from cocotb.log import SimLog

# Test parameters — env-driven so the Makefile depth/clock matrix can override
# them (mirrors the WR_MODE/RD_MODE pattern). The RTL receives FIFO_DEPTH /
# ALMOST_FULL / ALMOST_EMPTY via Icarus -P; the clock periods are Python-only.
DATA_WIDTH = 8
FIFO_DEPTH = int(os.environ.get("FIFO_DEPTH", "16"))
ALMOST_FULL = int(os.environ.get("ALMOST_FULL", "12"))
ALMOST_EMPTY = int(os.environ.get("ALMOST_EMPTY", "4"))

WR_CLK_PERIOD = int(os.environ.get("WR_CLK_PERIOD", "10"))   # default 100 MHz
RD_CLK_PERIOD = int(os.environ.get("RD_CLK_PERIOD", "13"))   # default ~77 MHz

WR_MODE = os.environ.get("WR_MODE", "LEVEL").upper()
RD_MODE = os.environ.get("RD_MODE", "LEVEL").upper()

import logging

log = SimLog("rrfifo_async_test")
log.setLevel(logging.INFO)  # surface info (seed, rail flags) in the sim log


# ---------------------------------------------------------------------------
# Clock / reset helpers
# ---------------------------------------------------------------------------
def start_clocks(dut):
    """Launch the two independent domain clocks."""
    cocotb.start_soon(Clock(dut.wr_clk_i, WR_CLK_PERIOD, units="ns").start(start_high=False))
    cocotb.start_soon(Clock(dut.rd_clk_i, RD_CLK_PERIOD, units="ns").start(start_high=False))


async def reset_dut(dut):
    """Reset BOTH domains together (required — see module header)."""
    dut.wr_en_i.value = 0
    dut.rd_en_i.value = 0
    dut.wr_data_i.value = 0
    dut.wr_rst_n_i.value = 0
    dut.rd_rst_n_i.value = 0
    # Hold reset across several cycles of the slower clock
    await Timer(RD_CLK_PERIOD * 5, units="ns")
    dut.wr_rst_n_i.value = 1
    dut.rd_rst_n_i.value = 1
    await Timer(RD_CLK_PERIOD * 2, units="ns")
    log.info("Reset complete (both domains)")


# ---------------------------------------------------------------------------
# Transfer helpers — one transfer per call, mode-agnostic (single-cycle pulse)
# ---------------------------------------------------------------------------
async def wait_not_full(dut, timeout=500):
    cycles = 0
    while int(dut.full_o.value) == 1:
        await RisingEdge(dut.wr_clk_i)
        cycles += 1
        if cycles > timeout:
            raise TimeoutError("wait_not_full timed out — FIFO stuck full")


async def wait_not_empty(dut, timeout=500):
    cycles = 0
    while int(dut.empty_o.value) == 1:
        await RisingEdge(dut.rd_clk_i)
        cycles += 1
        if cycles > timeout:
            raise TimeoutError("wait_not_empty timed out — FIFO stuck empty")


async def await_pointers_settled(dut, stable_cycles=4, timeout=2000):
    """Wait until the two domains' occupancy views converge and hold.

    After the last transfer, the Gray pointers still need SYNC_STAGES cycles
    to cross into the opposite domain. This polls on the slower clock until
    wr_level_o == rd_level_o and that equality is stable for `stable_cycles`
    consecutive samples — i.e. all in-flight pointer updates have propagated
    both ways. Replaces the ad-hoc `while rd_level < prime` / wait_empty_again
    polling. Tier 2 reuses this.
    """
    slow_clk = dut.wr_clk_i if WR_CLK_PERIOD >= RD_CLK_PERIOD else dut.rd_clk_i
    cycles = 0
    stable = 0
    while True:
        await RisingEdge(slow_clk)
        await Timer(1, units="ns")  # let level NBAs settle before sampling
        wl = int(dut.wr_level_o.value)
        rl = int(dut.rd_level_o.value)
        if wl == rl:
            stable += 1
            if stable >= stable_cycles:
                return wl
        else:
            stable = 0
        cycles += 1
        if cycles > timeout:
            raise TimeoutError(
                f"pointers never settled (wr_level={wl}, rd_level={rl})")


async def write_word(dut, data):
    """Write one word (waits for space). Single-cycle enable -> works in both modes."""
    await wait_not_full(dut)
    dut.wr_data_i.value = data & ((1 << DATA_WIDTH) - 1)
    dut.wr_en_i.value = 1
    await RisingEdge(dut.wr_clk_i)
    dut.wr_en_i.value = 0
    await RisingEdge(dut.wr_clk_i)
    log.debug(f"wrote 0x{data:02x} (wr_level={int(dut.wr_level_o.value)}, full={int(dut.full_o.value)})")


async def read_word(dut):
    """Read one word (waits for data). Registered non-FWFT: sample after 2nd edge."""
    await wait_not_empty(dut)
    dut.rd_en_i.value = 1
    await RisingEdge(dut.rd_clk_i)
    dut.rd_en_i.value = 0
    # rd_data_o is registered: valid on the edge after rd_valid
    await RisingEdge(dut.rd_clk_i)
    data = int(dut.rd_data_o.value)
    log.debug(f"read 0x{data:02x} (rd_level={int(dut.rd_level_o.value)}, empty={int(dut.empty_o.value)})")
    return data


# ===========================================================================
# Tests
# ===========================================================================
@cocotb.test()
async def test_reset_state(dut):
    """Reset asserts empty, clears full/overflow/underflow, zeroes levels."""
    try:
        log.info(f"=== reset test (WR_MODE={WR_MODE}, RD_MODE={RD_MODE}) ===")
        start_clocks(dut)
        await reset_dut(dut)
        assert int(dut.empty_o.value) == 1, "empty_o not set after reset"
        assert int(dut.full_o.value) == 0, "full_o set after reset"
        assert int(dut.overflow_o.value) == 0, "overflow_o set after reset"
        assert int(dut.underflow_o.value) == 0, "underflow_o set after reset"
        assert int(dut.wr_level_o.value) == 0, f"wr_level nonzero after reset: {int(dut.wr_level_o.value)}"
        assert int(dut.rd_level_o.value) == 0, f"rd_level nonzero after reset: {int(dut.rd_level_o.value)}"
        assert int(dut.almost_empty_o.value) == 1, "almost_empty_o not set after reset"
        assert int(dut.almost_full_o.value) == 0, "almost_full_o set after reset"
        log.info("reset test passed")
    except Exception as e:
        log.error(f"reset test failed: {e}\n{traceback.format_exc()}")
        raise


@cocotb.test()
async def test_single_word(dut):
    """Write one word, read it back across the clock boundary."""
    try:
        start_clocks(dut)
        await reset_dut(dut)
        data = random.randint(0, (1 << DATA_WIDTH) - 1)
        await write_word(dut, data)
        got = await read_word(dut)
        assert got == data, f"single-word mismatch: wrote 0x{data:02x}, read 0x{got:02x}"
        # Drained -> empty again (give the pointer time to cross back)
        await wait_empty_again(dut)
        log.info("single-word test passed")
    except Exception as e:
        log.error(f"single-word test failed: {e}\n{traceback.format_exc()}")
        raise


async def wait_empty_again(dut, timeout=500):
    cycles = 0
    while int(dut.empty_o.value) == 0:
        await RisingEdge(dut.rd_clk_i)
        cycles += 1
        if cycles > timeout:
            raise TimeoutError("FIFO never returned to empty")


@cocotb.test()
async def test_multi_word_order(dut):
    """FIFO ordering preserved across domains for a burst of words."""
    try:
        start_clocks(dut)
        await reset_dut(dut)
        n = FIFO_DEPTH // 2
        words = [random.randint(0, (1 << DATA_WIDTH) - 1) for _ in range(n)]
        for w in words:
            await write_word(dut, w)
        for i, expected in enumerate(words):
            got = await read_word(dut)
            assert got == expected, f"order mismatch at {i}: expected 0x{expected:02x}, got 0x{got:02x}"
        log.info("multi-word ordering test passed")
    except Exception as e:
        log.error(f"multi-word test failed: {e}\n{traceback.format_exc()}")
        raise


@cocotb.test()
async def test_fill_full_then_drain(dut):
    """Fill to capacity (full_o asserts), then drain (empty_o asserts), data intact."""
    try:
        start_clocks(dut)
        await reset_dut(dut)
        words = [random.randint(0, (1 << DATA_WIDTH) - 1) for _ in range(FIFO_DEPTH)]
        for w in words:
            await write_word(dut, w)
        # After FIFO_DEPTH writes with no reads, the FIFO must be full.
        assert int(dut.full_o.value) == 1, f"full_o not asserted when full (wr_level={int(dut.wr_level_o.value)})"
        assert int(dut.almost_full_o.value) == 1, "almost_full_o not asserted when full"
        for i, expected in enumerate(words):
            got = await read_word(dut)
            assert got == expected, f"drain mismatch at {i}: expected 0x{expected:02x}, got 0x{got:02x}"
        await wait_empty_again(dut)
        assert int(dut.empty_o.value) == 1, "empty_o not asserted after full drain"
        log.info("fill/drain test passed")
    except Exception as e:
        log.error(f"fill/drain test failed: {e}\n{traceback.format_exc()}")
        raise


@cocotb.test()
async def test_overflow(dut):
    """Writing into a full FIFO pulses overflow_o and drops the extra word."""
    try:
        start_clocks(dut)
        await reset_dut(dut)
        for i in range(FIFO_DEPTH):
            await write_word(dut, i)
        assert int(dut.full_o.value) == 1, "FIFO not full before overflow attempt"
        # Attempt one more write while full (raw, since write_word would wait forever)
        dut.wr_data_i.value = 0xEE
        dut.wr_en_i.value = 1
        await RisingEdge(dut.wr_clk_i)
        await Timer(1, units="ns")  # let the registered overflow_o NBA settle
        ovf = int(dut.overflow_o.value)
        dut.wr_en_i.value = 0
        await RisingEdge(dut.wr_clk_i)
        await Timer(1, units="ns")
        assert ovf == 1, "overflow_o not pulsed when writing to a full FIFO"
        assert int(dut.overflow_o.value) == 0, "overflow_o not a 1-cycle pulse"
        log.info("overflow test passed")
    except Exception as e:
        log.error(f"overflow test failed: {e}\n{traceback.format_exc()}")
        raise


@cocotb.test()
async def test_underflow(dut):
    """Reading from an empty FIFO pulses underflow_o."""
    try:
        start_clocks(dut)
        await reset_dut(dut)
        assert int(dut.empty_o.value) == 1, "FIFO not empty at start"
        dut.rd_en_i.value = 1
        await RisingEdge(dut.rd_clk_i)
        await Timer(1, units="ns")  # let the registered underflow_o NBA settle
        udf = int(dut.underflow_o.value)
        dut.rd_en_i.value = 0
        await RisingEdge(dut.rd_clk_i)
        await Timer(1, units="ns")
        assert udf == 1, "underflow_o not pulsed when reading an empty FIFO"
        assert int(dut.underflow_o.value) == 0, "underflow_o not a 1-cycle pulse"
        log.info("underflow test passed")
    except Exception as e:
        log.error(f"underflow test failed: {e}\n{traceback.format_exc()}")
        raise


@cocotb.test()
async def test_thresholds(dut):
    """almost_full asserts by the time we're full; almost_empty by the time near-empty."""
    try:
        start_clocks(dut)
        await reset_dut(dut)
        # almost_full must be set no later than ALMOST_FULL entries
        for i in range(ALMOST_FULL):
            await write_word(dut, i)
        assert int(dut.almost_full_o.value) == 1, (
            f"almost_full_o not asserted by {ALMOST_FULL} entries "
            f"(wr_level={int(dut.wr_level_o.value)})")
        # Drain everything; almost_empty must be set once at/under ALMOST_EMPTY
        while int(dut.empty_o.value) == 0:
            await read_word(dut)
        assert int(dut.almost_empty_o.value) == 1, "almost_empty_o not asserted when empty"
        log.info("threshold test passed")
    except Exception as e:
        log.error(f"threshold test failed: {e}\n{traceback.format_exc()}")
        raise


@cocotb.test()
async def test_concurrent_rw(dut):
    """Sustained simultaneous read+write keeps occupancy roughly constant, data intact."""
    try:
        start_clocks(dut)
        await reset_dut(dut)
        # Prime with a few entries
        primed = [random.randint(0, (1 << DATA_WIDTH) - 1) for _ in range(FIFO_DEPTH // 2)]
        for w in primed:
            await write_word(dut, w)

        # Concurrent streams via two coroutines
        n = 32
        stream = [random.randint(0, (1 << DATA_WIDTH) - 1) for _ in range(n)]
        received = []

        async def writer():
            for w in stream:
                await write_word(dut, w)

        async def reader():
            for _ in range(len(primed) + n):
                received.append(await read_word(dut))

        wr_task = cocotb.start_soon(writer())
        rd_task = cocotb.start_soon(reader())
        await wr_task
        await rd_task

        expected = primed + stream
        assert received == expected, "concurrent r/w data mismatch (FIFO ordering broken)"
        log.info("concurrent r/w test passed")
    except Exception as e:
        log.error(f"concurrent r/w test failed: {e}\n{traceback.format_exc()}")
        raise


@cocotb.test()
async def test_wr_mode_semantics(dut):
    """
    Hold wr_en_i high for several cycles with no reads, then inspect occupancy.
    LEVEL: one write per cycle -> multiple entries.
    PULSE: only the first rising edge writes -> exactly one entry.
    """
    try:
        start_clocks(dut)
        await reset_dut(dut)
        # hold must stay below full so the LEVEL branch never hits the full
        # edge mid-burst (which would drop writes and fail the == hold check).
        hold = max(1, FIFO_DEPTH - 1)
        dut.wr_data_i.value = 0xA5
        dut.wr_en_i.value = 1
        for _ in range(hold):
            await RisingEdge(dut.wr_clk_i)
        dut.wr_en_i.value = 0
        await RisingEdge(dut.wr_clk_i)
        await RisingEdge(dut.wr_clk_i)
        level = int(dut.wr_level_o.value)
        if WR_MODE == "PULSE":
            assert level == 1, f"PULSE write held high should write exactly 1, got {level}"
            # A second pulse (drop already happened) adds exactly one more
            dut.wr_en_i.value = 1
            await RisingEdge(dut.wr_clk_i)
            dut.wr_en_i.value = 0
            await RisingEdge(dut.wr_clk_i)
            await RisingEdge(dut.wr_clk_i)
            assert int(dut.wr_level_o.value) == 2, "second write pulse did not add one entry"
            log.info("write PULSE-mode semantics passed")
        else:
            assert level == hold, f"LEVEL write held {hold} cycles should write {hold}, got {level}"
            log.info("write LEVEL-mode semantics passed")
    except Exception as e:
        log.error(f"wr_mode semantics test failed: {e}\n{traceback.format_exc()}")
        raise


@cocotb.test()
async def test_rd_mode_semantics(dut):
    """
    Prime the FIFO, hold rd_en_i high for several cycles, inspect how many words left.
    LEVEL: one read per cycle. PULSE: only the first rising edge reads.
    """
    try:
        start_clocks(dut)
        await reset_dut(dut)
        # prime must fit the FIFO (write_word waits for not-full, so priming
        # more than DEPTH with no reads would deadlock). hold must leave at
        # least one word behind so `remaining` is non-empty (LEVEL branch).
        prime = min(6, FIFO_DEPTH)
        hold = min(4, prime - 1)
        words = [0x10 + i for i in range(prime)]
        for w in words:
            await write_word(dut, w)
        # Wait until ALL primed writes have crossed into the read domain (the write
        # pointer propagates through SYNC_STAGES flops), so the burst below isn't
        # starved by an in-flight pointer.
        cyc = 0
        while int(dut.rd_level_o.value) < prime:
            await RisingEdge(dut.rd_clk_i)
            cyc += 1
            if cyc > 500:
                raise TimeoutError("primed writes never fully crossed into read domain")

        # Hold rd_en_i high for several cycles.
        dut.rd_en_i.value = 1
        for _ in range(hold):
            await RisingEdge(dut.rd_clk_i)
        dut.rd_en_i.value = 0
        await RisingEdge(dut.rd_clk_i)
        await RisingEdge(dut.rd_clk_i)

        # Drain whatever is left and count it — robust against pointer lag and also
        # verifies the surviving words are the correct (later) ones.
        remaining = []
        while int(dut.empty_o.value) == 0:
            remaining.append(await read_word(dut))
        consumed = prime - len(remaining)

        if RD_MODE == "PULSE":
            assert consumed == 1, f"PULSE read held high should consume exactly 1, consumed {consumed}"
            assert remaining == words[1:], f"PULSE remaining words wrong: {[hex(w) for w in remaining]}"
            log.info("read PULSE-mode semantics passed")
        else:
            assert consumed == hold, f"LEVEL read held {hold} cycles should consume {hold}, consumed {consumed}"
            assert remaining == words[hold:], f"LEVEL remaining words wrong: {[hex(w) for w in remaining]}"
            log.info("read LEVEL-mode semantics passed")
    except Exception as e:
        log.error(f"rd_mode semantics test failed: {e}\n{traceback.format_exc()}")
        raise


# ===========================================================================
# B. Randomized concurrent stress + scoreboard
# ===========================================================================
@cocotb.test()
async def test_random_stress(dut):
    """Randomized concurrent read/write with a committed-transfer scoreboard.

    Independent stimulus coroutines drive wr_en/rd_en with random stalls.
    Independent *monitor* coroutines own the scoreboard and record only
    DUT-committed transfers (wr_en & ~full, rd_en & ~empty) — immune to the
    stall/edge races that plague stimulus-side bookkeeping. A deque enforces
    FIFO order; (seq, byte) tuples give diagnosable failure messages despite
    the 8-bit value wrap.

    Three phases provably visit both rails (latched saw_full / saw_empty),
    and a continuous level-bounds monitor (Tier 1's slice of item G) asserts
    0 <= levels <= DEPTH throughout.
    """
    try:
        seed = int(os.environ.get("RRFIFO_SEED", "0xC0FFEE"), 0)
        rng = random.Random(seed)
        log.info(f"=== random stress (seed={seed:#x}, WR_MODE={WR_MODE}, "
                 f"RD_MODE={RD_MODE}, DEPTH={FIFO_DEPTH}) ===")

        start_clocks(dut)
        await reset_dut(dut)

        mask = (1 << DATA_WIDTH) - 1

        # Scoreboard: committed writes waiting to be read back, in FIFO order.
        scoreboard = collections.deque()
        wr_seq = 0          # absolute write sequence number (for diagnostics)
        rd_count = 0        # committed reads checked
        saw_full = False
        saw_empty = False

        # Stimulus control: each phase sets the per-direction stall probability.
        # done flags let the monitors exit once stimulus is finished.
        ctrl = {"p_wr_stall": 0.0, "p_rd_stall": 0.0,
                "wr_done": False, "rd_done": False}

        # ----- write monitor: records committed writes on wr_clk -----------
        async def write_monitor():
            nonlocal wr_seq, saw_full
            while not ctrl["wr_done"] or int(dut.wr_en_i.value):
                await RisingEdge(dut.wr_clk_i)
                # wr_valid = wr_en_eff & ~full_o is combinational off PRE-edge
                # full_o. Sample the commit decision and the latched wr_data_i
                # at the RAW edge (the exact inputs the RTL committed), before
                # the write stimulus advances its data for the next cycle.
                committed = int(dut.wr_en_eff.value) and not int(dut.full_o.value)
                byte = int(dut.wr_data_i.value) & mask
                await Timer(1, units="ns")  # settle before sampling full_o flag
                if int(dut.full_o.value):
                    saw_full = True
                if committed:
                    scoreboard.append((wr_seq, byte))
                    wr_seq += 1

        # ----- read monitor: checks committed reads on rd_clk --------------
        # rd_valid = rd_en_eff & ~empty_o is combinational off the PRE-edge
        # empty_o. Sampling it post-settle would wrongly reject the read that
        # drains the last word (empty_o rises in that same step). So we read
        # the commit decision at the RAW edge (pre-NBA, = pre-edge state, the
        # exact condition the RTL used), then read the registered rd_data_o
        # post-settle — which holds the just-read word at the SAME edge the
        # read commits (verified empirically for both isolated and back-to-
        # back reads). saw_empty uses the post-settle empty_o.
        async def read_monitor():
            nonlocal rd_count, saw_empty
            while True:
                await RisingEdge(dut.rd_clk_i)
                committed = int(dut.rd_en_eff.value) and not int(dut.empty_o.value)
                await Timer(1, units="ns")  # let this edge's NBAs settle
                if int(dut.empty_o.value):
                    saw_empty = True
                if committed:
                    got = int(dut.rd_data_o.value) & mask
                    assert scoreboard, (
                        "committed read with empty scoreboard — "
                        "DUT delivered a word never written")
                    exp_seq, exp_byte = scoreboard.popleft()
                    assert got == exp_byte, (
                        f"read data mismatch at seq {exp_seq}: "
                        f"expected 0x{exp_byte:02x}, got 0x{got:02x}")
                    rd_count += 1
                if ctrl["rd_done"] and not int(dut.rd_en_i.value):
                    return

        # ----- continuous level-bounds monitor (item G slice) --------------
        async def bounds_monitor():
            while True:
                await RisingEdge(dut.wr_clk_i)
                await Timer(1, units="ns")
                wl = int(dut.wr_level_o.value)
                rl = int(dut.rd_level_o.value)
                assert 0 <= wl <= FIFO_DEPTH, f"wr_level out of bounds: {wl}"
                assert 0 <= rl <= FIFO_DEPTH, f"rd_level out of bounds: {rl}"

        # ----- write stimulus ---------------------------------------------
        async def write_stim(n_words):
            nonlocal wr_seq
            data = 0
            done = 0
            while done < n_words:
                if rng.random() < ctrl["p_wr_stall"]:
                    dut.wr_en_i.value = 0
                    await RisingEdge(dut.wr_clk_i)
                    continue
                # Present a fresh byte; only advance the data pattern when the
                # word actually commits (i.e. not full). The commit decision is
                # combinational off the PRE-edge full_o, so sample it at the raw
                # edge (pre-NBA) — sampling post-settle would miss the write
                # that lands on the becoming-full edge and loop forever.
                dut.wr_data_i.value = data & mask
                dut.wr_en_i.value = 1
                await RisingEdge(dut.wr_clk_i)
                if int(dut.wr_en_eff.value) and not int(dut.full_o.value):
                    data += 1
                    done += 1
                # In PULSE mode the enable must drop before the next transfer.
                if WR_MODE == "PULSE":
                    dut.wr_en_i.value = 0
                    await RisingEdge(dut.wr_clk_i)
            dut.wr_en_i.value = 0

        # ----- read stimulus -----------------------------------------------
        async def read_stim(n_words):
            done = 0
            while done < n_words:
                if rng.random() < ctrl["p_rd_stall"]:
                    dut.rd_en_i.value = 0
                    await RisingEdge(dut.rd_clk_i)
                    continue
                dut.rd_en_i.value = 1
                await RisingEdge(dut.rd_clk_i)
                # Pre-edge empty_o decides the commit (combinational), so count
                # at the raw edge — post-settle would miss the read draining the
                # last word and never reach n_words.
                if int(dut.rd_en_eff.value) and not int(dut.empty_o.value):
                    done += 1
                if RD_MODE == "PULSE":
                    dut.rd_en_i.value = 0
                    await RisingEdge(dut.rd_clk_i)
            dut.rd_en_i.value = 0

        # Launch the monitors (they outlive individual phases).
        wmon = cocotb.start_soon(write_monitor())
        rmon = cocotb.start_soon(read_monitor())
        bmon = cocotb.start_soon(bounds_monitor())

        # Each phase pushes AND pulls the same word count, so neither stimulus
        # starves (a reader asked for more reads than total writes would block
        # on an empty FIFO forever). The rail excursions come from the stall
        # ASYMMETRY during the run, not from unequal counts:
        #   Phase 1: reader stalls hard -> backlog builds -> full_o asserts.
        #   Phase 2: writer stalls hard -> FIFO drains faster than refilled
        #            -> empty_o asserts (reader idles on empty between writes).
        #   Phase 3: balanced moderate stalls for the bulk.
        P_RAIL = max(FIFO_DEPTH * 6, 80)
        TOTAL_BULK = 2000

        async def run_all():
            # Phase 1 — fill rail.
            ctrl["p_wr_stall"] = 0.0
            ctrl["p_rd_stall"] = 0.85
            wt = cocotb.start_soon(write_stim(P_RAIL))
            rt = cocotb.start_soon(read_stim(P_RAIL))
            await wt
            await rt

            # Phase 2 — drain rail.
            ctrl["p_wr_stall"] = 0.85
            ctrl["p_rd_stall"] = 0.0
            wt = cocotb.start_soon(write_stim(P_RAIL))
            rt = cocotb.start_soon(read_stim(P_RAIL))
            await wt
            await rt

            # Phase 3 — balanced bulk.
            ctrl["p_wr_stall"] = 0.3
            ctrl["p_rd_stall"] = 0.3
            wt = cocotb.start_soon(write_stim(TOTAL_BULK))
            rt = cocotb.start_soon(read_stim(TOTAL_BULK))
            await wt
            await rt

        # Global watchdog — uncapped phase waits live under one timeout.
        await with_timeout(run_all(), 5_000_000, "ns")

        ctrl["wr_done"] = True
        ctrl["rd_done"] = True

        # Let the read side drain everything the writer committed.
        drain_guard = 0
        while scoreboard or int(dut.empty_o.value) == 0:
            dut.rd_en_i.value = 1
            await RisingEdge(dut.rd_clk_i)
            if RD_MODE == "PULSE":
                dut.rd_en_i.value = 0
                await RisingEdge(dut.rd_clk_i)
            drain_guard += 1
            if drain_guard > 20000:
                raise TimeoutError(
                    f"stress drain stuck: {len(scoreboard)} words left, "
                    f"empty={int(dut.empty_o.value)}")
        dut.rd_en_i.value = 0
        # Give the read monitor a few edges to flush its pending pop.
        for _ in range(5):
            await RisingEdge(dut.rd_clk_i)
            await Timer(1, units="ns")

        # Join the monitors. write_monitor/read_monitor exit on their own
        # conditions; kill the never-terminating bounds monitor explicitly so
        # it cannot fire a spurious late assertion after the pass.
        await wmon
        await rmon
        bmon.kill()

        log.info(f"stress: wr_seq={wr_seq} committed writes, "
                 f"rd_count={rd_count} committed reads checked, "
                 f"scoreboard_remaining={len(scoreboard)}")
        log.info(f"stress: saw_full={saw_full}, saw_empty={saw_empty}, seed={seed:#x}")

        assert saw_full, "stress never observed full_o (fill rail not reached)"
        assert saw_empty, "stress never observed empty_o (drain rail not reached)"
        assert len(scoreboard) == 0, (
            f"{len(scoreboard)} committed words never read back")
        assert rd_count == wr_seq, (
            f"read count {rd_count} != committed write count {wr_seq}")
        assert wr_seq >= TOTAL_BULK, (
            f"scoreboard processed only {wr_seq} words, expected >= {TOTAL_BULK}")
        log.info("random stress test passed")
    except Exception as e:
        log.error(f"random stress test failed: {e}\n{traceback.format_exc()}")
        raise


# ===========================================================================
# D. Overflow / underflow data-integrity
# ===========================================================================
@cocotb.test()
async def test_overflow_integrity(dut):
    """Fill to DEPTH with a known pattern, hammer writes while full, then drain.

    A rejected write must neither store data nor advance wr_bin: the drained
    sequence must equal the original 0..DEPTH-1 pattern, in order, with the
    FIFO emptying cleanly. Also pins the LEVEL-vs-PULSE overflow behaviour:
    held-high wr_en overflows every cycle in LEVEL but exactly once in PULSE.
    """
    try:
        start_clocks(dut)
        await reset_dut(dut)
        mask = (1 << DATA_WIDTH) - 1
        pattern = [i & mask for i in range(FIFO_DEPTH)]
        for w in pattern:
            await write_word(dut, w)
        assert int(dut.full_o.value) == 1, (
            f"FIFO not full after {FIFO_DEPTH} writes "
            f"(wr_level={int(dut.wr_level_o.value)})")

        # Hammer wr_en high for several cycles while full, counting overflow
        # pulses. LEVEL: one pulse per cycle. PULSE: exactly one (first edge),
        # since the enable never drops.
        hammer = 5
        dut.wr_data_i.value = 0xEE  # must NOT be stored
        dut.wr_en_i.value = 1
        ovf_pulses = 0
        for _ in range(hammer):
            await RisingEdge(dut.wr_clk_i)
            await Timer(1, units="ns")
            ovf_pulses += int(dut.overflow_o.value)
        dut.wr_en_i.value = 0
        await RisingEdge(dut.wr_clk_i)
        await Timer(1, units="ns")

        if WR_MODE == "PULSE":
            assert ovf_pulses == 1, (
                f"PULSE held-high should overflow exactly once, got {ovf_pulses}")
        else:
            assert ovf_pulses == hammer, (
                f"LEVEL held-high should overflow every cycle ({hammer}), "
                f"got {ovf_pulses}")

        assert int(dut.full_o.value) == 1, "FIFO should still be full after rejected writes"
        assert int(dut.wr_level_o.value) == FIFO_DEPTH, (
            f"wr_bin advanced on a rejected write: wr_level={int(dut.wr_level_o.value)}")

        # Drain and verify the original pattern survived intact and in order.
        got = []
        for _ in range(FIFO_DEPTH):
            got.append(await read_word(dut))
        assert got == pattern, (
            f"overflow corrupted FIFO contents: expected {pattern}, got {got}")
        await await_pointers_settled(dut)
        assert int(dut.empty_o.value) == 1, "FIFO did not empty cleanly after overflow drain"
        assert int(dut.wr_level_o.value) == 0 and int(dut.rd_level_o.value) == 0, (
            "levels nonzero after clean drain")
        log.info("overflow integrity test passed")
    except Exception as e:
        log.error(f"overflow integrity test failed: {e}\n{traceback.format_exc()}")
        raise


@cocotb.test()
async def test_underflow_integrity(dut):
    """Spurious reads on an empty FIFO must not move the read pointer.

    From empty, pulse several reads (underflow). empty_o must stay 1 and
    rd_level_o must stay 0 throughout. Then write one word and read it back:
    if the read pointer had drifted, the readback would mismatch. Proves the
    rejected reads left wr/rd pointers in sync.
    """
    try:
        start_clocks(dut)
        await reset_dut(dut)
        assert int(dut.empty_o.value) == 1, "FIFO not empty at start"

        hammer = 5
        dut.rd_en_i.value = 1
        for _ in range(hammer):
            await RisingEdge(dut.rd_clk_i)
            await Timer(1, units="ns")
            assert int(dut.empty_o.value) == 1, "empty_o dropped during underflow"
            assert int(dut.rd_level_o.value) == 0, (
                f"rd pointer moved during underflow: rd_level={int(dut.rd_level_o.value)}")
            if RD_MODE == "PULSE":
                dut.rd_en_i.value = 0
                await RisingEdge(dut.rd_clk_i)
                dut.rd_en_i.value = 1
        dut.rd_en_i.value = 0
        await RisingEdge(dut.rd_clk_i)
        await Timer(1, units="ns")

        # Write one word, read it back: pointers must still be in sync.
        token = 0x5A
        await write_word(dut, token)
        got = await read_word(dut)
        assert got == token, (
            f"post-underflow readback mismatch: wrote 0x{token:02x}, "
            f"got 0x{got:02x} (read pointer drifted)")
        await await_pointers_settled(dut)
        assert int(dut.empty_o.value) == 1, "FIFO not empty after readback"
        log.info("underflow integrity test passed")
    except Exception as e:
        log.error(f"underflow integrity test failed: {e}\n{traceback.format_exc()}")
        raise


# ===========================================================================
# E. Threshold boundary precision
# ===========================================================================
@cocotb.test()
async def test_threshold_boundaries(dut):
    """Pin the exact almost_full / almost_empty transition points.

    Write-only then read-only, so there is NO concurrency: with zero reads
    rd_bin_sync stays 0 and wr_level_o is exact (almost_full rides wr_level);
    after settling, with zero writes the read view of wr_bin is fully crossed
    so rd_level_o is exact. That makes the boundary assertions exact rather
    than conservative.

    almost_full_o == (wr_level >= ALMOST_FULL): must be 0 while count <
    ALMOST_FULL, 1 at count == ALMOST_FULL (pins the >= off-by-one, line 149).
    almost_empty_o == (rd_level <= ALMOST_EMPTY): drain one at a time, must be
    0 while rd_level > ALMOST_EMPTY, 1 at rd_level <= ALMOST_EMPTY (pins line
    150). Mode-agnostic: write_word/read_word pulse the enable one cycle, so
    they behave identically under LEVEL and PULSE.
    """
    try:
        log.info(f"=== threshold boundaries (DEPTH={FIFO_DEPTH}, "
                 f"AF={ALMOST_FULL}, AE={ALMOST_EMPTY}) ===")
        start_clocks(dut)
        await reset_dut(dut)

        # --- almost_full transition (write-only, levels exact) ---
        for count in range(1, FIFO_DEPTH + 1):
            await write_word(dut, count & ((1 << DATA_WIDTH) - 1))
            await Timer(1, units="ns")  # settle the level/flag NBAs
            wl = int(dut.wr_level_o.value)
            assert wl == count, (
                f"write-only wr_level inexact: count={count}, wr_level={wl}")
            af = int(dut.almost_full_o.value)
            if count < ALMOST_FULL:
                assert af == 0, (
                    f"almost_full asserted early at count={count} "
                    f"(< ALMOST_FULL={ALMOST_FULL})")
            else:
                assert af == 1, (
                    f"almost_full not asserted at count={count} "
                    f"(>= ALMOST_FULL={ALMOST_FULL})")

        # Now full; let the read domain see the final write pointer so the
        # read-side level is exact before we start draining.
        rl = await await_pointers_settled(dut)
        assert rl == FIFO_DEPTH, f"settled level != DEPTH: {rl}"

        # --- almost_empty transition (read-only, levels exact) ---
        # Drain one word at a time; after each read settles, rd_level_o reflects
        # the remaining occupancy exactly (no concurrent writes).
        for read_idx in range(FIFO_DEPTH):
            await read_word(dut)
            # rd_level updates registered in the read domain — settle then sample.
            await Timer(1, units="ns")
            rl = int(dut.rd_level_o.value)
            remaining = FIFO_DEPTH - 1 - read_idx
            assert rl == remaining, (
                f"read-only rd_level inexact: expected {remaining}, got {rl}")
            ae = int(dut.almost_empty_o.value)
            if rl <= ALMOST_EMPTY:
                assert ae == 1, (
                    f"almost_empty not asserted at rd_level={rl} "
                    f"(<= ALMOST_EMPTY={ALMOST_EMPTY})")
            else:
                assert ae == 0, (
                    f"almost_empty asserted early at rd_level={rl} "
                    f"(> ALMOST_EMPTY={ALMOST_EMPTY})")
        # AE=0 boundary: almost_empty must assert only once truly empty (rl==0),
        # which is the rl <= ALMOST_EMPTY branch above with ALMOST_EMPTY==0.
        log.info("threshold boundaries test passed")
    except Exception as e:
        log.error(f"threshold boundaries test failed: {e}\n{traceback.format_exc()}")
        raise


# ===========================================================================
# F. Mid-operation reset recovery
# ===========================================================================
@cocotb.test()
async def test_reset_recovery(dut):
    """Asserting BOTH resets mid-traffic returns the FIFO to a clean state.

    Fill partway with traffic, drop wr_rst_n_i AND rd_rst_n_i together for
    several slow-clock cycles, release, settle, and verify the FIFO is fully
    cleared: empty, not full, zero levels, no stale over/underflow. Then push
    one word through to confirm it is functionally clean post-reset.

    Single-domain reset is spec-disallowed (module header: "wr_rst_n_i and
    rd_rst_n_i must be asserted together; resetting only one domain leaves
    occupancy undefined"), so it is deliberately NOT tested here.
    """
    try:
        log.info(f"=== reset recovery (DEPTH={FIFO_DEPTH}) ===")
        start_clocks(dut)
        await reset_dut(dut)

        # Fill partway with traffic (cap below DEPTH so it never wedges full).
        fill = max(1, FIFO_DEPTH // 2)
        for i in range(fill):
            await write_word(dut, (0x30 + i) & ((1 << DATA_WIDTH) - 1))
        await Timer(1, units="ns")
        assert int(dut.wr_level_o.value) > 0, "FIFO not primed before reset"

        # Assert BOTH resets together for several cycles of the slower clock.
        dut.wr_en_i.value = 0
        dut.rd_en_i.value = 0
        dut.wr_rst_n_i.value = 0
        dut.rd_rst_n_i.value = 0
        slow_period = max(WR_CLK_PERIOD, RD_CLK_PERIOD)
        await Timer(slow_period * 5, units="ns")
        dut.wr_rst_n_i.value = 1
        dut.rd_rst_n_i.value = 1
        await Timer(slow_period * 2, units="ns")

        # Settle the cross-domain pointer views, then assert a fully clean state.
        level = await await_pointers_settled(dut)
        assert level == 0, f"levels did not converge to 0 after reset: {level}"
        assert int(dut.empty_o.value) == 1, "empty_o not set after reset recovery"
        assert int(dut.full_o.value) == 0, "full_o set after reset recovery"
        assert int(dut.wr_level_o.value) == 0, "wr_level nonzero after reset recovery"
        assert int(dut.rd_level_o.value) == 0, "rd_level nonzero after reset recovery"
        assert int(dut.overflow_o.value) == 0, "overflow_o stale after reset recovery"
        assert int(dut.underflow_o.value) == 0, "underflow_o stale after reset recovery"

        # Functional confidence: one clean write/read round-trip post-reset.
        token = 0x77
        await write_word(dut, token)
        got = await read_word(dut)
        assert got == token, (
            f"post-reset round-trip mismatch: wrote 0x{token:02x}, got 0x{got:02x}")
        await await_pointers_settled(dut)
        assert int(dut.empty_o.value) == 1, "FIFO not empty after post-reset round-trip"
        log.info("reset recovery test passed")
    except Exception as e:
        log.error(f"reset recovery test failed: {e}\n{traceback.format_exc()}")
        raise


# ===========================================================================
# G. Conservative-level invariants
# ===========================================================================
@cocotb.test()
async def test_level_invariants(dut):
    """The headline design property: wr_level over-counts, rd_level under-counts.

    Drive the writer ahead of a lagging reader and assert THROUGHOUT that
    wr_level_o >= rd_level_o (the conservative bias) and both stay in
    [0, DEPTH]. The two occupancy views are sampled in different domains and
    only converge at quiescence, so equality is NOT asserted during traffic.
    After traffic stops and the pointers settle, wr_level_o == rd_level_o ==
    actual committed-but-unread count.

    Mode-agnostic: write_word / read_word pulse the enable one cycle.
    """
    try:
        log.info(f"=== level invariants (DEPTH={FIFO_DEPTH}) ===")
        start_clocks(dut)
        await reset_dut(dut)
        mask = (1 << DATA_WIDTH) - 1

        # Continuous invariant monitor: bias direction + absolute bounds. Sample
        # on the slower clock after settle so both registered level views are
        # stable for the comparison.
        slow_clk = dut.wr_clk_i if WR_CLK_PERIOD >= RD_CLK_PERIOD else dut.rd_clk_i

        async def invariant_monitor():
            while True:
                await RisingEdge(slow_clk)
                await Timer(1, units="ns")
                wl = int(dut.wr_level_o.value)
                rl = int(dut.rd_level_o.value)
                assert 0 <= wl <= FIFO_DEPTH, f"wr_level out of bounds: {wl}"
                assert 0 <= rl <= FIFO_DEPTH, f"rd_level out of bounds: {rl}"
                assert wl >= rl, (
                    f"conservative bias violated: wr_level={wl} < rd_level={rl} "
                    "(wr must over-count, rd must under-count)")

        mon = cocotb.start_soon(invariant_monitor())

        # Writer races ahead; reader lags. Track the true committed count so the
        # quiescent equality check has a ground-truth reference. Keep writes
        # capped at DEPTH so write_word never wedges on a full FIFO.
        written = 0
        read = 0
        n_writes = FIFO_DEPTH
        # Reader consumes only a fraction during traffic, leaving a backlog.
        n_reads_during = max(1, FIFO_DEPTH // 3)

        async def writer():
            nonlocal written
            for i in range(n_writes):
                await write_word(dut, i & mask)
                written += 1

        async def reader():
            nonlocal read
            # Lag deliberately: a few idle cycles between reads.
            for _ in range(n_reads_during):
                for _ in range(3):
                    await RisingEdge(dut.rd_clk_i)
                await read_word(dut)
                read += 1

        wt = cocotb.start_soon(writer())
        rt = cocotb.start_soon(reader())
        await wt
        await rt

        # Traffic stopped. Settle and check the views converge to the true count.
        dut.wr_en_i.value = 0
        dut.rd_en_i.value = 0
        level = await await_pointers_settled(dut)
        actual = written - read
        assert level == actual, (
            f"quiescent level {level} != actual count {actual} "
            f"(written={written}, read={read})")
        wl = int(dut.wr_level_o.value)
        rl = int(dut.rd_level_o.value)
        assert wl == rl == actual, (
            f"views did not converge to actual: wr_level={wl}, rd_level={rl}, "
            f"actual={actual}")

        mon.kill()  # stop before draining so it can't fire a late assertion
        log.info(f"level invariants test passed (settled count={actual})")
    except Exception as e:
        log.error(f"level invariants test failed: {e}\n{traceback.format_exc()}")
        raise
