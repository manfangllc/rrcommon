# Makefile for rrfifo cocotb testbench

# Build directory setup (MUST BE AT TOP)
SIM_BUILD := sim_build
$(shell mkdir -p $(SIM_BUILD))

# Simulator selection
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Source files
VERILOG_SOURCES = $(shell pwd)/rrfifo.sv

# Top level module
TOPLEVEL = rrfifo

# Test module
MODULE = test_rrfifo

# Enable SystemVerilog support
COMPILE_ARGS += -g2012

# Enable waveform dumping
WAVES=1
COMPILE_ARGS += -DWAVES=1

# VVP arguments for waveform dumping
VVP_ARGS = -M $(shell cocotb-config --lib-dir) -m libcocotbvpi_icarus
VVP_ARGS += +vcd=$(SIM_BUILD)/$(TOPLEVEL).vcd
VVP_ARGS += +fst=$(SIM_BUILD)/$(TOPLEVEL).fst

# Simulator output configuration
COCOTB_RESULTS_FILE := $(SIM_BUILD)/results.xml
VLOG_LOG_FILE := $(SIM_BUILD)/vlog_compile.log
VSIM_LOG_FILE := $(SIM_BUILD)/vsim_run.log
SIM_ARGS += -l$(SIM_BUILD)/sim.log

# Python path for cocotb
export PYTHONPATH := $(shell pwd):$(PYTHONPATH)

# Additional simulator arguments for better debug output
COMPILE_ARGS += -DDEBUG=1
COMPILE_ARGS += -DDUMP_LEVEL=9

# Force simulation to run
.PHONY: sim
sim: $(SIM_BUILD)
	$(MAKE) -C $(SIM_BUILD) -f ../Makefile

# Run simulation with coverage
.PHONY: coverage
coverage: COMPILE_ARGS += -DCOVERAGE
coverage: sim

# Clean targets
.PHONY: clean_waves
clean_waves:
	rm -rf $(SIM_BUILD)/*.vcd
	rm -rf $(SIM_BUILD)/*.fst

.PHONY: clean_logs
clean_logs:
	rm -rf $(SIM_BUILD)/*.log
	rm -rf $(SIM_BUILD)/*.xml

.PHONY: clean_all
clean_all: clean clean_waves clean_logs
	rm -rf $(SIM_BUILD)

# Include cocotb makefiles
include $(shell cocotb-config --makefiles)/Makefile.sim 