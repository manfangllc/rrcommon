# RRSPI - SPI Slave Interface Module

A flexible, synthesizable SystemVerilog SPI (Serial Peripheral Interface) slave module with configurable command and data widths.

## Features

- Configurable command and data widths
- Support for standard SPI mode (CPOL=0, CPHA=0)
- Separate command and data phases
- Tri-state MISO output when not selected
- Synchronous design with active-low reset
- Transfer completion indication

## Parameters

| Parameter   | Description                  | Default Value |
|-------------|------------------------------|---------------|
| CMD_WIDTH   | Command width in bits        | 16            |
| DATA_WIDTH  | Data width in bits           | 8             |

## Port Interface

### System Signals
| Port  | Direction | Width | Description                   |
|-------|-----------|-------|-------------------------------|
| clk   | input     | 1     | System clock                  |
| rst_n | input     | 1     | Active-low asynchronous reset |

### SPI Interface
| Port  | Direction | Width | Description                            |
|-------|-----------|-------|----------------------------------------|
| sclk  | input     | 1     | SPI clock from master                  |
| cs_n  | input     | 1     | Chip select (active low)               |
| mosi  | input     | 1     | Master Out Slave In (data from master) |
| miso  | output    | 1     | Master In Slave Out (data to master)   |

### Control and Data Interface
| Port          | Direction | Width       | Description                       |
|---------------|-----------|-------------|-----------------------------------|
| cmd_received  | output    | 1           | Command received indicator        |
| cmd           | output    | CMD_WIDTH   | Received command                  |
| rx_data       | output    | DATA_WIDTH  | Received data from master         |
| tx_data       | input     | DATA_WIDTH  | Data to transmit to master        |
| transfer_done | output    | 1           | Transfer complete indicator       |

## Functional Description

The SPI slave module operates as follows:

1. **Idle State**:
   - Module waits for the chip select (cs_n) to be asserted low
   - MISO output is tri-stated (high impedance)

2. **Command Phase**:
   - Upon cs_n assertion, module enters command reception mode
   - Samples CMD_WIDTH bits from MOSI on rising edge of SCLK
   - Upon completion, asserts cmd_received and transitions to data phase
   - Command is available on cmd output

3. **Data Phase**:
   - Samples DATA_WIDTH bits from MOSI into rx_data register
   - Simultaneously transmits tx_data to master via MISO
   | Updates MISO on falling edge of SCLK
   - Upon completion, asserts transfer_done
   - Data received from master is available on rx_data output

4. **End of Transfer**:
   - Transfer completes when full data width is transmitted or cs_n deasserts
   - Module returns to idle state when cs_n is deasserted

## SPI Protocol

This module implements an SPI slave with the following properties:
- CPOL = 0 (Clock polarity: idle low)
- CPHA = 0 (Clock phase: sample on rising edge, setup on falling edge)
- MSB first data transmission
- Command followed by data transfer

## Timing Diagram

```
        ┌─┐   ┌─┐   ┌─┐   ┌─┐         ┌─┐   ┌─┐   ┌─┐   ┌─┐
SCLK    │ └───┘ └───┘ └───┘ └─ ... ───┘ └───┘ └───┘ └───┘ └───
      ──┘                                                    └──
         
        ┌───────────────────── ... ────────────────────────┐
CS_N  ──┘                                                   └───
         
        ┌───┐   ┌───┐   ┌───┐         ┌───┐   ┌───┐   ┌───┐
MOSI  ──┤CMD│...│CMD│───┤DAT│─ ... ───┤DAT│...│DAT│───┤DAT│────
        └───┘   └───┘   └───┘         └───┘   └───┘   └───┘
         
      Z ┌───┐   ┌───┐   ┌───┐         ┌───┐   ┌───┐   ┌───┐ Z
MISO  ──┤   │...│   │───┤Bit│─ ... ───┤Bit│...│Bit│───┤Bit│────
        └───┘   └───┘   └───┘         └───┘   └───┘   └───┘
        
              Command Phase           Data Phase
```

## Usage Examples

### Module Instantiation

```systemverilog
rr_spi_slave #(
  .CMD_WIDTH  (16),        // 16-bit command
  .DATA_WIDTH (32)         // 32-bit data
) spi_slave_inst (
  // System signals
  .clk           (system_clk),
  .rst_n         (system_rst_n),
  
  // SPI signals
  .sclk          (spi_sclk),
  .mosi          (spi_mosi),
  .cs_n          (spi_cs_n),
  .miso          (spi_miso),
  
  // Control and data signals
  .cmd_received  (spi_cmd_received),
  .cmd           (spi_cmd),
  .rx_data       (spi_rx_data),
  .tx_data       (spi_tx_data),
  .transfer_done (spi_transfer_done)
);
```

### Transaction Handling Example

```systemverilog
// Logic to handle incoming SPI commands
always_ff @(posedge clk or negedge rst_n) begin
  if (!rst_n) begin
    // Initialize registers
    tx_data_reg <= '0;
  end else begin
    // If a command was received, prepare response
    if (cmd_received) begin
      case (cmd)
        16'h0001: tx_data_reg <= status_register;
        16'h0002: tx_data_reg <= control_register;
        16'h0003: tx_data_reg <= device_id;
        default:  tx_data_reg <= 8'hFF; // Default/error response
      endcase
    end
    
    // When transfer is complete, process received data
    if (transfer_done) begin
      case (cmd)
        16'h8001: status_register <= rx_data;
        16'h8002: control_register <= rx_data;
        default: ; // Ignore unrecognized commands
      endcase
    end
  end
end

// Always provide the tx_data to the SPI module
assign tx_data = tx_data_reg;
```

## Notes

- The testbench file (`rr_spi_slave_tb.sv`) appears to be empty and needs to be implemented.
- This module can be extended to support multiple SPI modes by adding CPOL and CPHA parameters.
- For long commands or data, consider adding a FIFO interface for tx/rx data.
- The current implementation uses the system clock domain for SPI signal processing. For high-frequency SPI clock scenarios, consider implementing proper clock domain crossing. 