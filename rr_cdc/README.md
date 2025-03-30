# RR Clock Domain Crossing (rr_cdc)

A parameterized SystemVerilog module for safely transferring data between different clock domains. Provides multiple synchronization methods to accommodate different design requirements and latency/throughput trade-offs.

## Overview

Clock Domain Crossing (CDC) is a critical aspect of digital design where signals must traverse from one clock domain to another. This module provides three common CDC methods:

1. **Pulse Synchronization** - For transferring single-cycle events across domains
2. **Toggle Synchronization** - For transferring data with reduced latency
3. **Handshake Synchronization** - For reliable transfers with full handshaking

The module handles all the necessary synchronization logic to prevent metastability and ensure deterministic behavior.

## Features

- Three synchronization modes in a single module
- Configurable data width for passing multi-bit values
- Adjustable synchronizer chain length (2-3 stages recommended)
- Full valid/ready handshaking interface
- Safe reset strategy for both domains
- Clean SystemVerilog implementation with proper synchronous design

## Module Interface

### Parameters

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|-------------|
| `WIDTH` | Width of data bus | 1 | Any positive integer |
| `SYNC_STAGES` | Number of synchronizer flip-flop stages | 2 | 2-3 recommended for FPGA |
| `MODE` | Synchronization method | "PULSE" | "PULSE", "TOGGLE", "HANDSHAKE" |
| `RESET_VALUE` | Reset value for synchronizers | '0 | Any valid value for WIDTH |

### Ports

| Port Name | Direction | Width | Description |
|-----------|-----------|-------|-------------|
| `clk_src_i` | input | 1 | Source domain clock |
| `rst_src_n_i` | input | 1 | Source domain reset (active low) |
| `data_src_i` | input | WIDTH | Data to transfer from source to destination |
| `valid_src_i` | input | 1 | Source indicates data is valid |
| `ready_src_o` | output | 1 | CDC is ready to accept source data |
| `clk_dst_i` | input | 1 | Destination domain clock |
| `rst_dst_n_i` | input | 1 | Destination domain reset (active low) |
| `data_dst_o` | output | WIDTH | Synchronized data in destination domain |
| `valid_dst_o` | output | 1 | Synchronized data is valid in destination domain |
| `ready_dst_i` | input | 1 | Destination is ready to accept data |

## Mode Descriptions

### PULSE Mode

Used for transferring single-cycle events (pulses) from one clock domain to another.

- **Advantages:** Simple, low resource usage
- **Disadvantages:** Can miss events if pulses arrive too quickly
- **Use when:** Transferring infrequent events like button presses or triggers

In PULSE mode, a single-cycle pulse in the source domain is safely transferred to the destination domain as another single-cycle pulse, regardless of the clock frequencies.

### TOGGLE Mode

Signals new data by toggling a control bit rather than using level-based signaling.

- **Advantages:** Lower latency than handshaking, more robust than pulse
- **Disadvantages:** Can only detect transitions, not specific levels
- **Use when:** Moderate data transfer rates with less strict flow control

In TOGGLE mode, each new data word causes a toggle signal to flip its state. The destination domain detects edges on the synchronized toggle signal.

### HANDSHAKE Mode

Full request/acknowledge handshaking between domains for guaranteed data transfer.

- **Advantages:** Most reliable, flow-controlled data transfer
- **Disadvantages:** Higher latency due to round-trip handshaking
- **Use when:** Reliability is critical and latency is less important

In HANDSHAKE mode, the source domain asserts a request when data is valid, and waits for an acknowledge from the destination domain before sending new data.

## Timing Characteristics

| Mode | Latency (Best Case) | Throughput | Flow Control |
|------|---------------------|------------|-------------|
| PULSE | 2-3 cycles | 1 per N cycles | None |
| TOGGLE | 2-3 cycles | 1 per N cycles | None |
| HANDSHAKE | 4-6 cycles | 1 per 4-6 cycles | Full |

Where N is the number of source clock cycles between transfers.

## Usage Examples

### Pulse Mode (Event Transfer)

```systemverilog
// Transfer button press events between clock domains
rr_cdc #(
  .WIDTH(1),
  .MODE("PULSE")
) button_cdc (
  .clk_src_i    (ui_clk),
  .rst_src_n_i  (ui_rst_n),
  .data_src_i   (1'b1),             // Constant 1 as data isn't used for events
  .valid_src_i  (button_pressed),   // Single-cycle pulse when button pressed
  .ready_src_o  (),                 // Not used in simple pulse transfer
  
  .clk_dst_i    (sys_clk),
  .rst_dst_n_i  (sys_rst_n),
  .data_dst_o   (),                 // Not used in simple pulse transfer
  .valid_dst_o  (button_event),     // Synchronized button press event
  .ready_dst_i  (1'b1)              // Always ready to receive events
);
```

### Toggle Mode (Status Flag)

```systemverilog
// Transfer status updates from slow sensor domain to fast processing domain
rr_cdc #(
  .WIDTH(8),
  .MODE("TOGGLE")
) status_cdc (
  .clk_src_i    (sensor_clk),      // Slow clock domain
  .rst_src_n_i  (sensor_rst_n),
  .data_src_i   (sensor_status),   // Status register value
  .valid_src_i  (status_updated),  // Pulsed when status changes
  .ready_src_o  (cdc_ready),
  
  .clk_dst_i    (proc_clk),        // Fast clock domain
  .rst_dst_n_i  (proc_rst_n),
  .data_dst_o   (status_synced),   // Synchronized status in proc domain
  .valid_dst_o  (status_valid),    // Pulsed when new status received
  .ready_dst_i  (1'b1)             // Always ready to receive status
);
```

### Handshake Mode (FIFO Interface)

```systemverilog
// Connect a FIFO between two clock domains reliably
rr_cdc #(
  .WIDTH(32),
  .MODE("HANDSHAKE")
) fifo_cdc (
  .clk_src_i    (write_clk),
  .rst_src_n_i  (write_rst_n),
  .data_src_i   (fifo_data),       // Data from the FIFO
  .valid_src_i  (!fifo_empty),     // FIFO has data available
  .ready_src_o  (fifo_read),       // Signal to pop data from FIFO
  
  .clk_dst_i    (read_clk),
  .rst_dst_n_i  (read_rst_n),
  .data_dst_o   (proc_data),       // Data for the processor
  .valid_dst_o  (proc_valid),      // Data valid for processor
  .ready_dst_i  (proc_ready)       // Processor ready to accept data
);
```

## Implementation Details

The module implements three synchronization methods with these key components:

1. **Synchronizer Chain**: Multi-stage flip-flop chain to safely cross clock domains and prevent metastability
2. **Edge Detector**: Identifies transitions in the synchronized signals
3. **Mode-Specific Logic**: Controls flow based on the selected synchronization strategy

### Internal Sub-Module

The module includes an internal synchronizer chain sub-module:

- `sync_chain`: Implements a configurable multi-stage synchronizer

## Simulation

The module includes a comprehensive testbench (`rr_cdc_tb.sv`) that verifies:
- All three synchronization modes
- Data integrity across domain crossings
- Proper behavior with different clock frequencies
- Reset behavior in both domains

## Synthesis Results

The CDC module is lightweight in terms of FPGA resources:
- Uses flip-flops for synchronizer chains (2-3 per crossing signal)
- Uses simple combinational logic for control
- No special resources or IP cores required

## Integration Notes

When using this CDC module:

1. **ALWAYS** use at least 2 synchronizer stages to reduce metastability
2. Consider timing constraints:
   - Set `set_false_path` constraints between clock domains
   - Use `set_max_delay` constraints for multi-bit buses if needed
3. Consider frequency relationships:
   - PULSE mode works best when source events are spaced adequately
   - HANDSHAKE is recommended for high throughput or closely-spaced events
4. Reset considerations:
   - Both domains have independent resets for proper initialization
   - Ensure both resets are asserted during system startup 