# Makefile for fulladder simulation

# Defaults
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Source files
VERILOG_SOURCES = $(PWD)/fulladder.sv

# Top level module
TOPLEVEL = fulladder

# Python test file
MODULE = test_fulladder

# Enable waveform dump
WAVES = 1
VCDFILE = fulladder.vcd

# Include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim 