# RRFIFO_AXI - AXI-Compatible Parameterizable FIFO

A configurable, synthesizable SystemVerilog FIFO implementation with AXI-style valid/ready handshaking interface.

## Features

- AXI-style handshaking interfaces for both input and output
- Fully parameterizable data width and FIFO depth
- Almost full/empty flags with configurable thresholds
- Overflow and underflow protection with detection flags
- FIFO level indicator
- Synchronous design with active-low reset
- Single clock domain operation

## Parameters

| Parameter    | Description                            | Default Value |
|--------------|----------------------------------------|---------------|
| DATA_WIDTH   | Width of the data path in bits         | 32            |
| FIFO_DEPTH   | Number of entries in the FIFO          | 16            |
| ALMOST_FULL  | Threshold for almost_full flag         | 12            |
| ALMOST_EMPTY | Threshold for almost_empty flag        | 4             |

## Port Interface

### Clock and Reset
| Port  | Direction | Width | Description                   |
|-------|-----------|-------|-------------------------------|
| clk   | input     | 1     | System clock                  |
| rst_n | input     | 1     | Active-low asynchronous reset |

### AXI-Style Write Interface
| Port     | Direction | Width       | Description                                  |
|----------|-----------|-------------|----------------------------------------------|
| s_valid_i| input     | 1           | Source valid - indicates valid data to write |
| s_ready_o| output    | 1           | Source ready - indicates FIFO can accept data|
| s_data_i | input     | DATA_WIDTH  | Data to be written to the FIFO               |

### AXI-Style Read Interface
| Port     | Direction | Width       | Description                                 |
|----------|-----------|-------------|---------------------------------------------|
| m_valid_o| output    | 1           | Master valid - indicates valid data on output|
| m_ready_i| input     | 1           | Master ready - indicates downstream can accept|
| m_data_o | output    | DATA_WIDTH  | Data read from the FIFO                     |

### Status Signals
| Port          | Direction | Width                | Description                             |
|---------------|-----------|----------------------|-----------------------------------------|
| full_o        | output    | 1                    | Indicates FIFO is full                  |
| almost_full_o | output    | 1                    | Indicates FIFO is approaching full      |
| empty_o       | output    | 1                    | Indicates FIFO is empty                 |
| almost_empty_o| output    | 1                    | Indicates FIFO is approaching empty     |
| overflow_o    | output    | 1                    | Indicates write attempted when full     |
| underflow_o   | output    | 1                    | Indicates read attempted when empty     |
| level_o       | output    | $clog2(FIFO_DEPTH)+1 | Current number of entries in FIFO       |

## Functional Description

The FIFO operates using AXI-style valid/ready handshaking:

1. **Write Operation**:
   - A write transaction occurs when both `s_valid_i` and `s_ready_o` are high
   - `s_ready_o` is high when the FIFO is not full
   - The source sets `s_valid_i` and `s_data_i` until `s_ready_o` is asserted

2. **Read Operation**:
   - A read transaction occurs when both `m_valid_o` and `m_ready_i` are high
   - `m_valid_o` is high when the FIFO is not empty
   - The master sets `m_ready_i` to indicate it can accept data

3. **Status Signals**:
   - `full_o` and `empty_o` indicate the FIFO's basic status
   - `almost_full_o` and `almost_empty_o` provide early indicators for flow control
   - `overflow_o` is asserted when write is attempted while full
   - `underflow_o` is asserted when read is attempted while empty
   - `level_o` indicates the current fill level of the FIFO

## Usage Examples

### AXI Source (Writing to FIFO)

```systemverilog
// Prepare data to send
s_data_i = data_to_write;
s_valid_i = 1'b1;

// Wait for ready
while (!s_ready_o) @(posedge clk);

// Transaction complete at this clock edge
@(posedge clk);
s_valid_i = 1'b0;
```

### AXI Master (Reading from FIFO)

```systemverilog
// Signal ready to receive
m_ready_i = 1'b1;

// Wait for valid data
while (!m_valid_o) @(posedge clk);

// Capture data at this clock edge
read_data = m_data_o;
@(posedge clk);
m_ready_i = 1'b0;
```

### Module Instantiation

```systemverilog
rrfifo_axi #(
  .DATA_WIDTH   (64),        // 64-bit data path
  .FIFO_DEPTH   (32),        // 32 entries deep
  .ALMOST_FULL  (28),        // Almost full at 28 entries
  .ALMOST_EMPTY (4)          // Almost empty at 4 entries
) axi_fifo_inst (
  .clk           (system_clk),
  .rst_n         (system_rst_n),
  
  // AXI write interface
  .s_valid_i     (source_valid),
  .s_ready_o     (source_ready),
  .s_data_i      (source_data),
  
  // AXI read interface
  .m_valid_o     (master_valid),
  .m_ready_i     (master_ready),
  .m_data_o      (master_data),
  
  // Status signals
  .full_o        (fifo_full),
  .almost_full_o (fifo_almost_full),
  .empty_o       (fifo_empty),
  .almost_empty_o(fifo_almost_empty),
  .overflow_o    (fifo_overflow),
  .underflow_o   (fifo_underflow),
  .level_o       (fifo_level)
);
```

## Integration with AXI Systems

This FIFO is compatible with AXI interfaces and can be used as a buffer between:

1. AXI masters and slaves operating at different rates
2. Different clock domains (with proper clock domain crossing logic)
3. Data width conversion stages
4. Protocol translation modules

## Verification

A comprehensive testbench is provided in `rrfifo_axi_tb.sv` which verifies:
- Reset state
- AXI-style handshaking
- Stalled writes (valid without ready)
- Stalled reads (ready without valid)
- Full and empty conditions
- Almost full/empty thresholds 
- Overflow and underflow protection
- Back-to-back transactions 