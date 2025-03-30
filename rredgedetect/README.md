# RR Edge Detector (rredgedetect)

A parameterized SystemVerilog edge detector module that detects rising edges, falling edges, and any transition (toggle) on input signals. The module can be used for multiple bits in parallel.

## Overview

Edge detection is commonly used in digital designs for:
- Detecting button presses or releases
- Processing asynchronous signals
- Triggering state changes on signal transitions
- Clock domain crossing handshaking
- Implementing interrupts

This module registers the input signal and compares the current and previous values to identify transitions.

## Features

- Configurable bit width (default: 1-bit)
- Simultaneous detection of rising, falling, and toggle (any) edges
- Clean SystemVerilog implementation with proper synchronous design
- Active-low reset for FPGA designs

## Module Interface

### Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `WIDTH`   | Width of signals to monitor | 1 |

### Ports

| Port Name | Direction | Width | Description |
|-----------|-----------|-------|-------------|
| `clk_i`   | input     | 1     | Clock signal |
| `rst_n_i` | input     | 1     | Active-low reset |
| `signal_i`| input     | WIDTH | Input signal(s) to monitor for edges |
| `rise_o`  | output    | WIDTH | High for one clock cycle when a rising edge is detected |
| `fall_o`  | output    | WIDTH | High for one clock cycle when a falling edge is detected |
| `toggle_o`| output    | WIDTH | High for one clock cycle when any edge is detected |

## Usage Example

```systemverilog
// Instantiate a 1-bit edge detector
rredgedetect u_button_edge (
  .clk_i      (clk),
  .rst_n_i    (rst_n),
  .signal_i   (button_debounced),  // Input from a debouncer
  .rise_o     (button_pressed),    // Button press event
  .fall_o     (button_released),   // Button release event
  .toggle_o   ()                   // Unused in this example
);

// Instantiate a multi-bit edge detector
rredgedetect #(
  .WIDTH(8)
) u_data_edge (
  .clk_i      (clk),
  .rst_n_i    (rst_n),
  .signal_i   (data_in),          // 8-bit data input
  .rise_o     (data_rising_edge),  // Detect rising edges on each bit
  .fall_o     (data_falling_edge), // Detect falling edges on each bit
  .toggle_o   (data_changed)       // Detect any changes on each bit
);
```

## Timing Behavior

The edge detector has a one-cycle latency from signal change to edge detection. The output signals (`rise_o`, `fall_o`, `toggle_o`) are asserted for exactly one clock cycle per edge.

```
         _   _   _   _   _   _   _
clk_i   | |_| |_| |_| |_| |_| |_| |_
        
         ___________         _______
signal_i           |_______|
        
                   _
rise_o   _________|_|_______________
        
         _________________
fall_o                   |_|_______
        
                   _         _
toggle_o _________|_|_______|_|_____
```

## Implementation Details

The edge detector uses a simple register to store the previous state of the input signal, then performs bit-wise logical operations to determine the edges:

- Rising edges: current value is 1, previous value was 0 (`signal_i & ~signal_reg`)
- Falling edges: current value is 0, previous value was 1 (`~signal_i & signal_reg`)
- Any toggle: current and previous values differ (`signal_i ^ signal_reg`)

## Simulation

The module includes a comprehensive testbench (`rredgedetect_tb.sv`) that verifies:
- Single bit transitions
- Multiple bit transitions
- All bits rising and falling
- Random patterns
- Edge detection accuracy

## Synthesis Results

The edge detector is very lightweight in terms of FPGA resources:
- Uses `WIDTH` flip-flops for storing previous signal values
- Uses simple combinational logic for edge detection
- No special resources or IP cores required

## Integration Notes

This module is ideal for:
- Button/switch input processing
- Serial protocol implementations
- State machine triggers
- Interrupt generation 