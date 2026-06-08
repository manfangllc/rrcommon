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

import os
import random
import traceback

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge
from cocotb.log import SimLog

# Test parameters (must match the RTL defaults / Makefile overrides)
DATA_WIDTH = 8
FIFO_DEPTH = 16
ALMOST_FULL = 12
ALMOST_EMPTY = 4

WR_CLK_PERIOD = 10   # 100 MHz
RD_CLK_PERIOD = 13   # ~77 MHz — intentionally asynchronous to the write clock

WR_MODE = os.environ.get("WR_MODE", "LEVEL").upper()
RD_MODE = os.environ.get("RD_MODE", "LEVEL").upper()

log = SimLog("rrfifo_async_test")


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
        hold = 5
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
        prime = 6
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
        hold = 4
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
