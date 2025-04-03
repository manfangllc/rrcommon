# Makefile for rr_spi_slave cocotb testbench

# defaults
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Source files
VERILOG_SOURCES = $(shell pwd)/rr_spi_slave.sv

# Top level module
TOPLEVEL = rr_spi_slave

# Test module
MODULE = test_rr_spi_slave

# Simulator output file
SIM_ARGS += > sim.log 2>&1

include $(shell cocotb-config --makefiles)/Makefile.sim 