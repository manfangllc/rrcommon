# Makefile for rr_adder cocotb testbench

# defaults
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Source files
VERILOG_SOURCES = $(shell pwd)/rr_adder.sv

# Top level module
TOPLEVEL = rr_adder

# Test module
MODULE = test_rr_adder

# Simulator output file
SIM_ARGS += > sim.log 2>&1

include $(shell cocotb-config --makefiles)/Makefile.sim 