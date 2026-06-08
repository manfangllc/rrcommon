# Makefile for rrfifo_async cocotb testbench

# Build directory setup (MUST BE AT TOP)
SIM_BUILD := sim_build
$(shell mkdir -p $(SIM_BUILD))

# Simulator selection
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Source files: the async FIFO + sync_chain (lives inside rr_cdc.sv)
VERILOG_SOURCES = $(shell pwd)/rrfifo_async.sv
VERILOG_SOURCES += $(shell pwd)/../rr_cdc/rr_cdc.sv

# Top level module
TOPLEVEL = rrfifo_async

# Test module
MODULE = test_rrfifo_async

# Enable mode (overridable: make WR_MODE=PULSE RD_MODE=PULSE)
WR_MODE ?= LEVEL
RD_MODE ?= LEVEL

# Depth / threshold / clock matrix (overridable). The int params go into the
# RTL via -P (BARE ints — quoting makes Icarus treat them as strings and the
# elaboration math silently breaks). The clock periods are Python-only (read
# by the cocotb test, not the RTL). Constraints enforced by the DUT's $error
# (which does NOT abort Icarus, so keep them valid): ALMOST_FULL in [1,DEPTH],
# ALMOST_EMPTY in [0,DEPTH].
FIFO_DEPTH    ?= 16
ALMOST_FULL   ?= 12
ALMOST_EMPTY  ?= 4
WR_CLK_PERIOD ?= 10
RD_CLK_PERIOD ?= 13

# Pass the SV string params to Icarus, and export to the cocotb test so the
# testbench knows which semantics to expect.
COMPILE_ARGS += -g2012
COMPILE_ARGS += -Prrfifo_async.WR_MODE=\"$(WR_MODE)\"
COMPILE_ARGS += -Prrfifo_async.RD_MODE=\"$(RD_MODE)\"
COMPILE_ARGS += -Prrfifo_async.FIFO_DEPTH=$(FIFO_DEPTH)
COMPILE_ARGS += -Prrfifo_async.ALMOST_FULL=$(ALMOST_FULL)
COMPILE_ARGS += -Prrfifo_async.ALMOST_EMPTY=$(ALMOST_EMPTY)
export WR_MODE
export RD_MODE
export FIFO_DEPTH ALMOST_FULL ALMOST_EMPTY WR_CLK_PERIOD RD_CLK_PERIOD

# Enable waveform dumping
WAVES=1
COMPILE_ARGS += -DWAVES=1

# VVP arguments for waveform dumping
VVP_ARGS = -M $(shell cocotb-config --lib-dir) -m libcocotbvpi_icarus
VVP_ARGS += +vcd=$(SIM_BUILD)/$(TOPLEVEL).vcd
VVP_ARGS += +fst=$(SIM_BUILD)/$(TOPLEVEL).fst

# Simulator output configuration
COCOTB_RESULTS_FILE := $(SIM_BUILD)/results.xml
SIM_ARGS += -l$(SIM_BUILD)/sim.log

# Python path for cocotb
export PYTHONPATH := $(shell pwd):$(PYTHONPATH)

# Bare `make` MUST clean-compile first. Icarus does not rebuild on COMPILE_ARGS-only
# changes (only source mtimes), so a `sim_build/sim.vvp` left by a prior `make
# pulse_both` / `make depth4` would silently run the WRONG RTL config against the
# current env params — yielding false fails OR false passes depending on run order.
# So the default goal is `run`, which cleans then sims (command-line VAR=val
# overrides propagate to the sub-make automatically). All convenience targets below
# already clean first for the same reason; this just extends that safety to bare make.
.DEFAULT_GOAL := run
.PHONY: run
run:
	$(MAKE) clean && $(MAKE) sim

# Convenience targets for the mode matrix. Each does an explicit `clean` then
# invokes the explicit `sim` target (never the bare default) to avoid recursion.
.PHONY: pulse_wr pulse_rd pulse_both level
level:
	$(MAKE) clean && $(MAKE) sim WR_MODE=LEVEL RD_MODE=LEVEL
pulse_wr:
	$(MAKE) clean && $(MAKE) sim WR_MODE=PULSE RD_MODE=LEVEL
pulse_rd:
	$(MAKE) clean && $(MAKE) sim WR_MODE=LEVEL RD_MODE=PULSE
pulse_both:
	$(MAKE) clean && $(MAKE) sim WR_MODE=PULSE RD_MODE=PULSE

# A. Depth corner coverage. DEPTH=2 exercises the special-case generate branch
# (rrfifo_async.sv:131-134); depth2_pulse confirms it survives PULSE edge-detect.
# ALMOST_* scaled valid per depth (the DUT's $error won't abort Icarus).
.PHONY: depth2 depth4 depth2_pulse
depth2:
	$(MAKE) clean && $(MAKE) sim FIFO_DEPTH=2 ALMOST_FULL=2 ALMOST_EMPTY=1
depth4:
	$(MAKE) clean && $(MAKE) sim FIFO_DEPTH=4 ALMOST_FULL=3 ALMOST_EMPTY=1
depth2_pulse:
	$(MAKE) clean && $(MAKE) sim FIFO_DEPTH=2 ALMOST_FULL=2 ALMOST_EMPTY=1 WR_MODE=PULSE RD_MODE=PULSE

# C. Clock-ratio regimes. rd_faster flips to the empty-tending regime;
# near_equal stresses the beat-frequency / metastability window.
.PHONY: rd_faster near_equal
rd_faster:
	$(MAKE) clean && $(MAKE) sim WR_CLK_PERIOD=13 RD_CLK_PERIOD=10
near_equal:
	$(MAKE) clean && $(MAKE) sim WR_CLK_PERIOD=10 RD_CLK_PERIOD=11

# Clean targets
.PHONY: clean_waves clean_logs clean_all
clean_waves:
	rm -rf $(SIM_BUILD)/*.vcd $(SIM_BUILD)/*.fst
clean_logs:
	rm -rf $(SIM_BUILD)/*.log $(SIM_BUILD)/*.xml
clean_all: clean clean_waves clean_logs
	rm -rf $(SIM_BUILD)

# Include cocotb makefiles
include $(shell cocotb-config --makefiles)/Makefile.sim
