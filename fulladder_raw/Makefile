# Makefile for fulladder

# Defaults
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Module specific settings
VERILOG_SOURCES += $(PWD)/fulladder.sv
TOPLEVEL = fulladder
MODULE = test_fulladder

# Enable waveform dump
COMPILE_ARGS += -DVCD_DUMP

# Include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim 