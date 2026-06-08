#=============================================================================
# rrfifo_async — CDC timing constraints (SCOPED, reusable per instance)
#
# Apply scoped so the relative cell paths below resolve inside each
# rrfifo_async instance and the file is reused for every instantiation:
#
#   read_xdc -ref rrfifo_async -unmanaged rrfifo_async.xdc
#   # or, in a block-design / OOC flow:
#   set_property SCOPED_TO_REF rrfifo_async [get_files rrfifo_async.xdc]
#
# Assumes the parent design has already defined wr_clk_i and rd_clk_i as real,
# independent clocks. These constraints bound ONLY the metastability-safe
# crossings inside the module:
#   * the two Gray-pointer double-flop synchronizers (u_wr2rd, u_rd2wr)
#   * the dual-clock RAM data path
# Pair with (* ASYNC_REG = "TRUE" *) on the synchronizer flops (already set in
# rr_cdc.sv sync_chain) so each 2-flop chain is also placed tightly.
#
# STRATEGY NOTE — we deliberately do NOT 'set_clock_groups -asynchronous'
# between the two clocks here. A clock-group false path OUTRANKS set_max_delay
# and set_bus_skew, which would silently disable everything below and discard
# the Gray-bus skew guarantee. If you prefer the blanket approach, declare the
# async group at TOP level and delete this file — but you then lose the
# bus-skew bound that keeps the one-bit-per-step Gray property coherent through
# routing. The bounded form below is the safer default for a Gray-pointer FIFO.
#=============================================================================

#--- Crossing 1: write-domain Gray pointer -> read-domain synchronizer --------
set wr2rd_src [get_cells {wr_gray_reg[*]}]
set wr2rd_dst [get_cells {u_wr2rd/sync_stages_reg[0][*]}]
set rd_period [get_property -min PERIOD \
                 [get_clocks -of_objects \
                   [get_pins -filter {REF_PIN_NAME == C} -of_objects $wr2rd_dst]]]
set_max_delay -datapath_only -from $wr2rd_src -to $wr2rd_dst $rd_period
set_bus_skew                 -from $wr2rd_src -to $wr2rd_dst $rd_period

#--- Crossing 2: read-domain Gray pointer -> write-domain synchronizer --------
set rd2wr_src [get_cells {rd_gray_reg[*]}]
set rd2wr_dst [get_cells {u_rd2wr/sync_stages_reg[0][*]}]
set wr_period [get_property -min PERIOD \
                 [get_clocks -of_objects \
                   [get_pins -filter {REF_PIN_NAME == C} -of_objects $rd2wr_dst]]]
set_max_delay -datapath_only -from $rd2wr_src -to $rd2wr_dst $wr_period
set_bus_skew                 -from $rd2wr_src -to $rd2wr_dst $wr_period

#--- Dual-clock RAM data path (write domain -> rd_data_o capture) -------------
# Safe by construction: the Gray pointer cannot present a read address until the
# corresponding word is committed and stable, so this path only needs to be
# BOUNDED, not cycle-accurate. set_max_delay keeps the route short; a
# set_false_path is an acceptable looser alternative. The cell selector below
# may need adjustment after the synth pass depending on block vs distributed
# inference (BRAM -> RAMB*, distributed -> RAM* / mem_reg*) — verify with
# report_timing on this -from/-to once synthesized. The -quiet + length guard
# avoids erroring out if the name does not match this build's inference.
set mem_cells     [get_cells -quiet {mem_reg* mem_reg[*]*}]
set rd_data_cells [get_cells {rd_data_o_reg[*]}]
if {[llength $mem_cells]} {
  set_max_delay -datapath_only -from $mem_cells -to $rd_data_cells $rd_period
}
