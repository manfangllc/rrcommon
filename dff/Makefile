# Simulator selection
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Source files
VERILOG_SOURCES = $(shell pwd)/dff.sv

# Module configuration
TOPLEVEL = dff
MODULE = test_dff

# Set DATA_WIDTH parameter to 1
PARAMETER_OVERRIDES = "DATA_WIDTH=1"

# Enable SystemVerilog support
COMPILE_ARGS += -g2012

# Enable waveform dumping
WAVES=1

# Redirect output to log file
SIM_ARGS += > sim.log 2>&1

# Python path for cocotb
PYTHONPATH := $(shell pwd):$(PYTHONPATH)

# Include cocotb makefiles
include $(shell cocotb-config --makefiles)/Makefile.sim

# Additional targets for clean-up
.PHONY: clean_waves
clean_waves:
	rm -rf sim_build/*.vcd

.PHONY: clean_all
clean_all: clean clean_waves
	rm -f sim.log 