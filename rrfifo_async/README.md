# RRFIFO_ASYNC — Asynchronous (Dual-Clock) FIFO

A configurable, synthesizable SystemVerilog FIFO that safely moves data between
two **independent clock domains**, with a per-direction parameter selecting
**level** vs **pulse** enable semantics.

It is the clock-domain-crossing sibling of [`rrfifo`](../rrfifo/README.md): same
flag/threshold/protection feature set, but the write and read interfaces run on
separate clocks. Pointer crossing uses the classic Gray-code technique (Cliff
Cummings style), reusing the `sync_chain` double-flop synchronizer from
[`rr_cdc`](../rr_cdc/rr_cdc.sv).

## Features

- Independent write (`wr_clk_i`) and read (`rd_clk_i`) clock domains
- Gray-coded pointers + double-flop pointer synchronizers (metastability-safe)
- `full` / `empty` (glitch-free, from the Gray compare) plus
  `almost_full` / `almost_empty` thresholds
- Overflow / underflow protection with 1-cycle detection pulses
- **Split, conservative occupancy:** `wr_level_o` (write-domain, over-counts →
  safe against overflow) and `rd_level_o` (read-domain, under-counts → safe
  against underflow)
- Registered, **non-FWFT** read: `rd_data_o` is valid the cycle *after* `rd_en_i`
- Per-direction `WR_MODE` / `RD_MODE`:
  - **`"LEVEL"`** — one transfer per clock while the enable is held high (the
    behaviour of the synchronous `rrfifo`)
  - **`"PULSE"`** — one *rising edge* of the enable triggers exactly one
    transfer; the enable must return low and rise again for the next

## Parameters

| Parameter    | Description                                    | Default   |
|--------------|------------------------------------------------|-----------|
| DATA_WIDTH   | Data path width in bits                        | 8         |
| FIFO_DEPTH   | Entries — **must be a power of 2, ≥ 2**         | 16        |
| ALMOST_FULL  | `almost_full_o` threshold (entries)            | 12        |
| ALMOST_EMPTY | `almost_empty_o` threshold (entries)           | 4         |
| SYNC_STAGES  | Pointer synchronizer flop count (2–3 typical)  | 2         |
| WR_MODE      | Write enable mode: `"LEVEL"` or `"PULSE"`      | `"LEVEL"` |
| RD_MODE      | Read enable mode: `"LEVEL"` or `"PULSE"`       | `"LEVEL"` |
| RAM_STYLE    | `mem` inference hint (see below)               | `"auto"`  |

`FIFO_DEPTH` is checked at elaboration; a non-power-of-2 or `< 2` value raises a
SystemVerilog `$error`. The power-of-2 requirement comes from the Gray-pointer
full/empty comparison and is intrinsic to this style of async FIFO.

## Port Interface

### Write domain
| Port            | Dir | Width                | Description                         |
|-----------------|-----|----------------------|-------------------------------------|
| wr_clk_i        | in  | 1                    | Write clock                         |
| wr_rst_n_i      | in  | 1                    | Write-domain async reset (active-low)|
| wr_en_i         | in  | 1                    | Write enable (level- or pulse-gated)|
| wr_data_i       | in  | DATA_WIDTH           | Write data                          |
| full_o          | out | 1                    | FIFO full                           |
| almost_full_o   | out | 1                    | Occupancy ≥ ALMOST_FULL             |
| overflow_o      | out | 1                    | Write attempted while full (1-cycle)|
| wr_level_o      | out | $clog2(FIFO_DEPTH)+1 | Conservative occupancy (over-count) |

### Read domain
| Port            | Dir | Width                | Description                         |
|-----------------|-----|----------------------|-------------------------------------|
| rd_clk_i        | in  | 1                    | Read clock                          |
| rd_rst_n_i      | in  | 1                    | Read-domain async reset (active-low)|
| rd_en_i         | in  | 1                    | Read enable (level- or pulse-gated) |
| rd_data_o       | out | DATA_WIDTH           | Read data (valid cycle after rd_en) |
| empty_o         | out | 1                    | FIFO empty                          |
| almost_empty_o  | out | 1                    | Occupancy ≤ ALMOST_EMPTY            |
| underflow_o     | out | 1                    | Read attempted while empty (1-cycle)|
| rd_level_o      | out | $clog2(FIFO_DEPTH)+1 | Conservative occupancy (under-count)|

## Important usage notes

- **Reset both domains together.** `wr_rst_n_i` and `rd_rst_n_i` must be asserted
  overlapping to reset the FIFO. Each synchronizer is clocked/reset in its
  destination domain, so resetting only one side leaves the cross-domain pointer
  view (and therefore occupancy/full/empty) undefined until both have been reset.
  Drive them from a common reset that is released after both clocks are running.
- **Levels are conservative and lagged.** `wr_level_o` / `rd_level_o` are derived
  from a *synchronized* (and therefore delayed) copy of the opposite pointer, so
  each is biased in the safe direction and is a status/threshold metric — not a
  cycle-exact shared count (which is not obtainable in a true async FIFO). Use
  `full_o` / `empty_o` (from the Gray compare) for the hard go/no-go decision.
- **Non-FWFT read.** Assert `rd_en_i`; `rd_data_o` is valid on the following
  `rd_clk_i` edge. Identical timing to the synchronous `rrfifo`.

## Instantiation

```systemverilog
rrfifo_async #(
  .DATA_WIDTH   (32),
  .FIFO_DEPTH   (64),
  .ALMOST_FULL  (56),
  .ALMOST_EMPTY (8),
  .SYNC_STAGES  (2),
  .WR_MODE      ("LEVEL"),   // stream writes
  .RD_MODE      ("PULSE")    // one read per enable edge
) u_fifo (
  .wr_clk_i (adc_clk),   .wr_rst_n_i (adc_rst_n),
  .wr_en_i  (sample_vld), .wr_data_i (sample),
  .full_o   (), .almost_full_o (), .overflow_o (), .wr_level_o (),

  .rd_clk_i (sys_clk),   .rd_rst_n_i (sys_rst_n),
  .rd_en_i  (pop),       .rd_data_o (word),
  .empty_o  (no_data), .almost_empty_o (), .underflow_o (), .rd_level_o ()
);
```

## Verification

`test_rrfifo_async.py` is a CDC-aware cocotb testbench (Icarus). It runs two
independent clocks (10 ns write / 13 ns read) so the crossing is genuinely
exercised, and covers: reset state, single/multi-word ordering across domains,
fill-to-full + drain-to-empty, overflow/underflow pulses, almost_full/empty
thresholds, sustained concurrent read+write, and the LEVEL-vs-PULSE held-enable
semantics for each direction.

The `WR_MODE` / `RD_MODE` SV parameters are passed through to Icarus and exported
to the testbench (which adapts its expectations). Run the matrix:

```bash
make                       # LEVEL / LEVEL (default)
make pulse_wr              # PULSE write, LEVEL read
make pulse_rd              # LEVEL write, PULSE read
make pulse_both            # PULSE / PULSE
# or explicitly:
make clean_all && make sim WR_MODE=PULSE RD_MODE=PULSE
```

All four configurations pass 10/10. View waveforms with
`gtkwave sim_build/rrfifo_async.fst`.

## Synthesis & CDC closure

This module is **RTL-only — it instantiates no vendor primitives** (no `XPM_*`,
no `unisim` cells, no `RAMB`/`FIFO36E2`). The SystemVerilog source is the single
source of truth and simulates unchanged in Verilator. Mapping it cleanly and
*safely* onto a Xilinx FPGA needs three things, none of which break that:

1. **Synchronizer placement.** The `sync_chain` flops in
   [`rr_cdc.sv`](../rr_cdc/rr_cdc.sv) carry `(* ASYNC_REG = "TRUE" *)` so Vivado
   keeps each 2-flop chain placed tightly and out of SRL/RAM/DSP, preserving the
   metastability settling window (MTBF). This is a synthesis *attribute*, not a
   primitive — other tools ignore it.

2. **Memory inference.** `mem` is a textbook simple-dual-port array (one write
   clock, one registered read clock) and infers SDP RAM automatically. The
   `RAM_STYLE` parameter drives a `(* ram_style = ... *)` hint: `"auto"`
   (default) lets Vivado pick block vs distributed by depth; pin `"block"` /
   `"distributed"` / `"ultra"` per instance when you want the resource target
   deterministic. Again an attribute, not a primitive.

3. **Timing constraints.** [`rrfifo_async.xdc`](./rrfifo_async.xdc) is a
   **scoped** constraint file — apply it per instance:
   ```tcl
   read_xdc -ref rrfifo_async -unmanaged rrfifo_async.xdc
   ```
   It bounds the two Gray-pointer synchronizer crossings with
   `set_max_delay -datapath_only` (gives a metastable bit the full destination
   period to settle) plus `set_bus_skew` (Gray code changes exactly one bit per
   step — bounding inter-bit skew preserves that guarantee through routing). It
   deliberately avoids a blanket `set_clock_groups -asynchronous`, which would
   *outrank* and silently disable those bounds; see the header comment for the
   rationale and the blanket-approach alternative.

### `report_cdc` waiver — RAM data path

A CDC report (`report_cdc` / a lint pass) will flag the `mem` data path as an
unsynchronized crossing: it is written in the `wr_clk_i` domain and read in the
`rd_clk_i` domain with no synchronizer on the data bus. **This is safe by
construction and should be waived**, with this rationale:

> The read address is derived from a Gray pointer that is itself synchronized
> through the double-flop `sync_chain`. A read address therefore cannot point at
> a memory word until that word has been committed *and* the write pointer has
> propagated across the synchronizer — many cycles after the data was written
> and is stable. The data bus needs no synchronizer because the pointer
> handshake guarantees the data is static before any read can reach it. This is
> the standard Cummings-style async-FIFO RAM crossing.

The scoped XDC bounds this path with `set_max_delay -datapath_only` rather than
leaving it unconstrained (a `set_false_path` is an acceptable looser
alternative).

### Not yet done (deferred)

An out-of-context Vivado **synth + STA pass** to *prove* the above — zero
unwanted primitives, RAM inferred as intended, `ASYNC_REG` honored, constraints
applied, timing clean, and the RAM-path cell selector in the XDC confirmed
against this build's inference. The RTL, attributes, and constraint template are
in place; the synth/STA verification is the remaining step before silicon.
