/**
 * AXI-compatible parameterizable FIFO module
 *
 * This module implements a parameterizable synchronous FIFO with 
 * AXI-style valid/ready handshaking signals for input and output.
 * Features include:
 * - AXI-style handshaking protocol (valid/ready)
 * - Almost full/empty flags
 * - Overflow/underflow protection
 * - Parameterizable thresholds
 * - Data width and depth parameterization
 */
module rrfifo_axi #(
  parameter int DATA_WIDTH    = 32,
  parameter int FIFO_DEPTH    = 16,
  parameter int ALMOST_FULL   = 12,
  parameter int ALMOST_EMPTY  = 4
) (
  // Clock and reset
  input  logic                  clk,
  input  logic                  rst_n,
  
  // AXI-style write interface
  input  logic                  s_valid_i,    // Source valid signal
  output logic                  s_ready_o,    // Source ready signal 
  input  logic [DATA_WIDTH-1:0] s_data_i,     // Source data
  
  // AXI-style read interface
  output logic                  m_valid_o,    // Master valid signal
  input  logic                  m_ready_i,    // Master ready signal
  output logic [DATA_WIDTH-1:0] m_data_o,     // Master data
  
  // Status signals
  output logic                  full_o,
  output logic                  almost_full_o,
  output logic                  empty_o,
  output logic                  almost_empty_o,
  output logic                  overflow_o,
  output logic                  underflow_o,
  output logic [$clog2(FIFO_DEPTH):0] level_o
);

  // Local parameters
  localparam ADDR_WIDTH = $clog2(FIFO_DEPTH);
  
  // Internal signals
  logic [DATA_WIDTH-1:0]    mem [FIFO_DEPTH-1:0];
  logic [ADDR_WIDTH-1:0]    wr_ptr;
  logic [ADDR_WIDTH-1:0]    rd_ptr;
  logic [ADDR_WIDTH:0]      count;
  logic                     wr_valid;
  logic                     rd_valid;

  // AXI handshaking logic
  // Write is valid when source valid is high and FIFO is not full
  assign s_ready_o = ~full_o;  
  assign wr_valid = s_valid_i & s_ready_o;
  
  // Read is valid when FIFO is not empty and master is ready
  assign m_valid_o = ~empty_o;
  assign rd_valid = m_valid_o & m_ready_i;
  
  // Status signals
  assign full_o         = (count == FIFO_DEPTH);
  assign empty_o        = (count == 0);
  assign almost_full_o  = (count >= ALMOST_FULL);
  assign almost_empty_o = (count <= ALMOST_EMPTY);
  assign level_o        = count;
  
  // Memory write process
  always_ff @(posedge clk) begin
    if (wr_valid) begin
      mem[wr_ptr] <= s_data_i;
    end
  end

  // Read data output
  assign m_data_o = mem[rd_ptr];

  // FIFO pointers update logic
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      wr_ptr      <= '0;
      rd_ptr      <= '0;
      count       <= '0;
      overflow_o  <= 1'b0;
      underflow_o <= 1'b0;
    end else begin
      // Default values for overflow/underflow flags
      overflow_o  <= 1'b0;
      underflow_o <= 1'b0;
      
      // Handle write pointer
      if (wr_valid) begin
        wr_ptr <= (wr_ptr == FIFO_DEPTH - 1) ? '0 : wr_ptr + 1'b1;
      end
      
      // Handle read pointer
      if (rd_valid) begin
        rd_ptr <= (rd_ptr == FIFO_DEPTH - 1) ? '0 : rd_ptr + 1'b1;
      end
      
      // Update count based on simultaneous operations
      case ({wr_valid, rd_valid})
        2'b01: count <= count - 1'b1; // Read only
        2'b10: count <= count + 1'b1; // Write only
        2'b11: count <= count;        // Read and write simultaneously
        default: count <= count;      // No operation
      endcase
      
      // Detect overflow - writing when full with valid source
      if (s_valid_i && full_o) begin
        overflow_o <= 1'b1;
      end
      
      // Detect underflow - reading when empty with ready master
      if (m_ready_i && empty_o) begin
        underflow_o <= 1'b1;
      end
    end
  end

endmodule : rrfifo_axi 