# Makefile for RRPWM testbench

# Build directory setup
SIM_BUILD := sim_build
$(shell mkdir -p $(SIM_BUILD))

# Simulator selection
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Source files
VERILOG_SOURCES = $(shell pwd)/rrpwm.sv

# Top level module
TOPLEVEL = rrpwm

# Test module
MODULE = test_rrpwm

# Enable SystemVerilog support
COMPILE_ARGS += -g2012

# Enable waveform dumping
WAVES=1
COMPILE_ARGS += -DWAVES=1

# Simulator output configuration
COCOTB_RESULTS_FILE := $(SIM_BUILD)/results.xml
VLOG_LOG_FILE := $(SIM_BUILD)/vlog_compile.log
VSIM_LOG_FILE := $(SIM_BUILD)/vsim_run.log
SIM_ARGS += -l$(SIM_BUILD)/sim.log

# Python path for cocotb
export PYTHONPATH := $(shell pwd):$(PYTHONPATH)

# Force simulation to run
.PHONY: sim
sim: $(SIM_BUILD)
	$(MAKE) -C $(SIM_BUILD) -f ../Makefile

# Additional targets for clean-up
.PHONY: clean_waves
clean_waves:
	rm -rf $(SIM_BUILD)/*.vcd
	rm -rf $(SIM_BUILD)/*.fst

.PHONY: clean_all
clean_all: clean clean_waves
	rm -rf $(SIM_BUILD)

# Include cocotb makefiles
include $(shell cocotb-config --makefiles)/Makefile.sim 