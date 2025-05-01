# Full Adder with Cocotb Testbench

This directory contains a SystemVerilog implementation of a full adder along with a cocotb-based testbench.

## Files
- `fulladder.sv`: SystemVerilog implementation of the full adder
- `test_fulladder.py`: Cocotb testbench that verifies all possible input combinations
- `Makefile`: Build configuration for simulation

## Requirements
- Icarus Verilog
- Python 3.6+
- cocotb
- GTKWave (for viewing waveforms)

## Running the Tests
1. Make sure you have all requirements installed
2. Run the simulation:
   ```bash
   make
   ```
3. View the waveforms:
   ```bash
   gtkwave fulladder.vcd
   ```

## Expected Behavior
The testbench will:
1. Test all 8 possible input combinations (2³ for a, b, and cin)
2. Print the test results showing inputs, expected outputs, and actual outputs
3. Generate a waveform file (fulladder.vcd) for visualization

## Truth Table
| a | b | cin | sum | cout |
|---|---|-----|-----|------|
| 0 | 0 | 0   | 0   | 0    |
| 0 | 0 | 1   | 1   | 0    |
| 0 | 1 | 0   | 1   | 0    |
| 0 | 1 | 1   | 0   | 1    |
| 1 | 0 | 0   | 1   | 0    |
| 1 | 0 | 1   | 0   | 1    |
| 1 | 1 | 0   | 0   | 1    |
| 1 | 1 | 1   | 1   | 1    | 