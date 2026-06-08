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

# Pass the SV string params to Icarus, and export to the cocotb test so the
# testbench knows which semantics to expect.
COMPILE_ARGS += -g2012
COMPILE_ARGS += -Prrfifo_async.WR_MODE=\"$(WR_MODE)\"
COMPILE_ARGS += -Prrfifo_async.RD_MODE=\"$(RD_MODE)\"
export WR_MODE
export RD_MODE

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

# Bare `make` runs the cocotb sim (cocotb's own default goal), NOT a convenience
# target below — otherwise defining a target before the include hijacks it.
.DEFAULT_GOAL := sim

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
