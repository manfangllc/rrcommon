# Makefile for rredgedetect cocotb testbench

# defaults
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Source files
VERILOG_SOURCES = $(shell pwd)/rredgedetect.sv

# Top level module
TOPLEVEL = rredgedetect

# Test module
MODULE = test_rredgedetect

# Module parameters
COMPILE_ARGS = +define+WIDTH=4

include $(shell cocotb-config --makefiles)/Makefile.sim 