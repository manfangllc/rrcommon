# Makefile for rr_cdc testbench

# Defaults
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Source files
VERILOG_SOURCES = $(shell pwd)/rr_cdc.sv

# Module parameters
TOPLEVEL = rr_cdc
MODULE = test_rr_cdc

# Parameters for the test
PLUSARGS += +WIDTH=8 +SYNC_STAGES=2 +MODE=\"PULSE\" +RESET_VALUE=0

# Simulator output file
SIM_ARGS += > sim.log 2>&1

# Include cocotb's make rules
include $(shell cocotb-config --makefiles)/Makefile.sim 