# Makefile for rrfifo cocotb testbench

# defaults
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Source files
VERILOG_SOURCES = $(shell pwd)/rrfifo.sv

# Top level module
TOPLEVEL = rrfifo

# Test module
MODULE = test_rrfifo

# Simulator output file
SIM_ARGS += > sim.log 2>&1

include $(shell cocotb-config --makefiles)/Makefile.sim 