# RR PWM Generator (rrpwm)

A configurable, multi-channel Pulse Width Modulation (PWM) generator module implemented in SystemVerilog for FPGA designs. This module provides precise control over duty cycle and frequency for motor control, LED dimming, and other PWM applications.

## Overview

Pulse Width Modulation (PWM) is a technique that generates a digital signal with a variable duty cycle to simulate an analog output level. This module provides:

- Configurable counter resolution for flexible PWM frequency
- Multiple independent PWM channels with individual duty cycle control
- Enable/disable control for each channel
- Polarity selection (active high or active low outputs)
- Clean SystemVerilog implementation with proper synchronous design

## Features

- Parameterized design for easy customization
- Configurable number of output channels
- Runtime adjustable period and duty cycle values
- Selectable output polarity
- Per-channel enable/disable control
- Support for robust duty cycle handling (saturates values exceeding period)
- Default values for period and duty cycle

## Module Interface

### Parameters

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|-------------|
| `COUNTER_WIDTH` | Width of the counter (PWM resolution) | 8 | Any positive integer |
| `DEFAULT_PERIOD` | Default period value if input is zero | 255 | 0 to 2^COUNTER_WIDTH-1 |
| `DEFAULT_DUTY` | Default duty cycle if input is zero | 128 | 0 to DEFAULT_PERIOD |
| `NUM_CHANNELS` | Number of independent PWM channels | 1 | Any positive integer |
| `POLARITY` | Output polarity setting | 1 | 0=active low, 1=active high |

### Ports

| Port Name | Direction | Width | Description |
|-----------|-----------|-------|-------------|
| `clk_i` | input | 1 | Clock signal |
| `rst_n_i` | input | 1 | Active-low reset |
| `period_i` | input | COUNTER_WIDTH | Period register value |
| `enable_i` | input | NUM_CHANNELS | Enable mask for each channel |
| `duty_i` | input | COUNTER_WIDTH[NUM_CHANNELS] | Array of duty cycle values for each channel |
| `pwm_o` | output | NUM_CHANNELS | PWM output signals |

## Timing Characteristics

The PWM frequency is determined by:

```
PWM_Frequency = Clock_Frequency / (period_i + 1)
```

The duty cycle percentage is calculated as:

```
Duty_Cycle_Percentage = (duty_i / (period_i + 1)) × 100%
```

## Usage Examples

### Basic Single-Channel PWM

```systemverilog
// Single-channel PWM generator for LED dimming
rrpwm #(
  .COUNTER_WIDTH(8),         // 8-bit resolution
  .DEFAULT_PERIOD(255),      // 256 clock cycles per period
  .DEFAULT_DUTY(128),        // 50% default duty cycle
  .NUM_CHANNELS(1),          // Single channel
  .POLARITY(1)               // Active high output
) led_pwm (
  .clk_i(clk),               // System clock
  .rst_n_i(rst_n),           // System reset
  .period_i(pwm_period),     // Period control (0 = use default)
  .enable_i(led_enable),     // LED enable signal
  .duty_i('{led_brightness}),// LED brightness control
  .pwm_o(led_output)         // PWM output to LED
);
```

### Multi-Channel PWM for RGB LED Control

```systemverilog
// Three-channel PWM for RGB LED control
rrpwm #(
  .COUNTER_WIDTH(8),
  .DEFAULT_PERIOD(255),
  .DEFAULT_DUTY(0),          // Default off
  .NUM_CHANNELS(3),          // RGB = 3 channels
  .POLARITY(1)               // Active high outputs
) rgb_pwm (
  .clk_i(clk),
  .rst_n_i(rst_n),
  .period_i(color_period),   // Shared period for all channels
  .enable_i(rgb_enable),     // Per-color enable
  .duty_i('{red_value, green_value, blue_value}), // RGB values
  .pwm_o(rgb_outputs)        // [2:0] for R,G,B outputs
);
```

### Motor Control with Configurable Frequency

```systemverilog
// Dual-channel PWM for motor H-bridge control
rrpwm #(
  .COUNTER_WIDTH(12),        // 12-bit for fine control
  .DEFAULT_PERIOD(4095),     // 4096 count period
  .DEFAULT_DUTY(0),          // Default stopped
  .NUM_CHANNELS(2),          // Two channels for bidirectional control
  .POLARITY(1)               // Active high
) motor_controller (
  .clk_i(clk),
  .rst_n_i(rst_n),
  .period_i(motor_freq),     // Controls PWM frequency
  .enable_i(motor_enable),   // Enable signals
  .duty_i('{forward_speed, reverse_speed}), // Speed control
  .pwm_o(motor_drive)        // PWM outputs to H-bridge
);
```

## Implementation Details

The PWM generator is implemented as a simple counter-based design:

1. A counter increments on each clock cycle
2. When the counter reaches the period value, it resets to zero
3. Each PWM channel's output is high when the counter is less than its duty cycle value
4. Output polarity can be configured to be either active-high or active-low

The module includes logic to handle edge cases:
- When duty cycle exceeds period, it's automatically limited to the period value
- When period or duty values are 0, default values are used
- Output is controlled by enable signals for each channel

## PWM Waveform Example

```
         Period
      <------------->
      ____           ____
     |    |          |    |
     |    |          |    |
_____|    |__________|    |_____

     <---->
     Duty Cycle
```

## Simulation

The module includes a comprehensive testbench (`rrpwm_tb.sv`) that verifies:
- Single and multi-channel operation
- Various duty cycle settings
- Period changes during operation
- Enable/disable functionality
- Output polarity

## Synthesis Results

The PWM generator is lightweight in terms of FPGA resources:
- Uses a single counter (COUNTER_WIDTH bits) for all channels
- Each channel uses a comparator and output register
- No special resources or IP cores required

## Applications

The PWM module is ideal for:
- LED brightness control
- Motor speed control
- Digital-to-analog conversion
- Servo motor control
- Power regulation
- Audio generation (simple tones)

## Integration Notes

When using this PWM module:

1. Choose COUNTER_WIDTH based on your resolution needs:
   - Higher values give finer control but use more logic
   - Lower values offer less resolution but higher maximum frequencies

2. Calculate appropriate period and duty values:
   - For a specific frequency: period_i = (Clock_Freq / Target_PWM_Freq) - 1
   - For a specific duty cycle %: duty_i = (period_i + 1) * (Duty_Cycle_% / 100)

3. Consider output buffering:
   - When driving high-current loads, use appropriate output buffers or driver ICs
   - PWM outputs may require filtering for analog-like behavior

4. Resource sharing:
   - Multiple channels share the same counter, making this efficient for multi-channel applications 