# RRFIFO - Parameterizable Synchronous FIFO

A configurable, synthesizable SystemVerilog FIFO implementation with comprehensive status flags and protection mechanisms.

## Features

- Fully parameterizable data width and FIFO depth
- Almost full/empty flags with configurable thresholds
- Overflow and underflow protection with detection flags
- FIFO level indicator
- Synchronous design with active-low reset
- Single clock domain operation

## Parameters

| Parameter    | Description                            | Default Value |
|--------------|----------------------------------------|---------------|
| DATA_WIDTH   | Width of the data path in bits         | 8             |
| FIFO_DEPTH   | Number of entries in the FIFO          | 16            |
| ALMOST_FULL  | Threshold for almost_full flag         | 12            |
| ALMOST_EMPTY | Threshold for almost_empty flag        | 4             |

## Port Interface

### Clock and Reset
| Port  | Direction | Width | Description                   |
|-------|-----------|-------|-------------------------------|
| clk   | input     | 1     | System clock                  |
| rst_n | input     | 1     | Active-low asynchronous reset |

### Write Interface
| Port         | Direction | Width       | Description                             |
|--------------|-----------|-------------|-----------------------------------------|
| wr_en_i      | input     | 1           | Write enable signal                     |
| wr_data_i    | input     | DATA_WIDTH  | Data to be written to the FIFO          |
| full_o       | output    | 1           | Indicates FIFO is full                  |
| almost_full_o| output    | 1           | Indicates FIFO is approaching full      |
| overflow_o   | output    | 1           | Indicates write attempted when full     |

### Read Interface
| Port          | Direction | Width       | Description                             |
|---------------|-----------|-------------|-----------------------------------------|
| rd_en_i       | input     | 1           | Read enable signal                      |
| rd_data_o     | output    | DATA_WIDTH  | Data read from the FIFO                 |
| empty_o       | output    | 1           | Indicates FIFO is empty                 |
| almost_empty_o| output    | 1           | Indicates FIFO is approaching empty     |
| underflow_o   | output    | 1           | Indicates read attempted when empty     |

### Status
| Port    | Direction | Width                | Description                  |
|---------|-----------|----------------------|------------------------------|
| level_o | output    | $clog2(FIFO_DEPTH)+1 | Current number of entries    |

## Functional Description

The FIFO operates as follows:

1. Data is written to the FIFO when `wr_en_i` is asserted and the FIFO is not full
2. Data is read from the FIFO when `rd_en_i` is asserted and the FIFO is not empty
3. When the FIFO is full, `full_o` is asserted and further write attempts will set `overflow_o`
4. When the FIFO is empty, `empty_o` is asserted and further read attempts will set `underflow_o`
5. The FIFO operates in a circular buffer pattern, with internal pointers for read and write operations

## Usage Examples

### Basic Write and Read Operations

```systemverilog
// Write to FIFO
if (!full_o) begin
  wr_en_i = 1'b1;
  wr_data_i = data_to_write;
end else begin
  wr_en_i = 1'b0;
end

// Read from FIFO
if (!empty_o) begin
  rd_en_i = 1'b1;
  read_data = rd_data_o;
end else begin
  rd_en_i = 1'b0;
end
```

### Module Instantiation

```systemverilog
rrfifo #(
  .DATA_WIDTH   (32),        // 32-bit data path
  .FIFO_DEPTH   (64),        // 64 entries deep
  .ALMOST_FULL  (56),        // Almost full at 56 entries
  .ALMOST_EMPTY (8)          // Almost empty at 8 entries
) my_fifo_instance (
  .clk           (system_clk),
  .rst_n         (system_rst_n),
  
  // Write interface
  .wr_en_i       (write_enable),
  .wr_data_i     (write_data),
  .full_o        (fifo_full),
  .almost_full_o (fifo_almost_full),
  .overflow_o    (fifo_overflow),
  
  // Read interface
  .rd_en_i       (read_enable),
  .rd_data_o     (read_data),
  .empty_o       (fifo_empty),
  .almost_empty_o(fifo_almost_empty),
  .underflow_o   (fifo_underflow),
  
  // Status
  .level_o       (fifo_level)
);
```

## Verification

A comprehensive testbench is provided in `rrfifo_tb.sv` which verifies:
- Reset state
- Basic write/read operations
- Full and empty conditions
- Almost full/empty thresholds
- Overflow and underflow protection
- Back-to-back operations 