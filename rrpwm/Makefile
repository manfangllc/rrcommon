# Makefile for rrpwm cocotb testbench

# defaults
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Source files
VERILOG_SOURCES = $(shell pwd)/rrpwm.sv

# Top level module
TOPLEVEL = rrpwm

# Test module
MODULE = test_rrpwm

include $(shell cocotb-config --makefiles)/Makefile.sim 