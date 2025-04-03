/**
 * Parameterizable FIFO module
 *
 * This module implements a parameterizable synchronous FIFO with 
 * configurable data width and depth. Features include:
 * - Almost full/empty flags
 * - Overflow/underflow protection
 * - Parameterizable thresholds
 */
module rrfifo #(
  parameter int DATA_WIDTH    = 8,
  parameter int FIFO_DEPTH    = 16,
  parameter int ALMOST_FULL   = 12,
  parameter int ALMOST_EMPTY  = 4
) (
  // Clock and reset
  input  logic                  clk,
  input  logic                  rst_n,
  
  // Write interface
  input  logic                  wr_en_i,
  input  logic [DATA_WIDTH-1:0] wr_data_i,
  output logic                  full_o,
  output logic                  almost_full_o,
  output logic                  overflow_o,
  
  // Read interface
  input  logic                  rd_en_i,
  output logic [DATA_WIDTH-1:0] rd_data_o,
  output logic                  empty_o,
  output logic                  almost_empty_o,
  output logic                  underflow_o,
  
  // Status
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
  
  // Status flags
  assign empty_o = (count == 0);
  assign full_o = (count == FIFO_DEPTH);
  assign almost_empty_o = (count <= ALMOST_EMPTY);
  assign almost_full_o = (count >= ALMOST_FULL);
  assign level_o = count;
  
  // Operation validation
  assign wr_valid = wr_en_i && !full_o;
  assign rd_valid = rd_en_i && !empty_o;
  
  // Memory write process
  always_ff @(posedge clk) begin
    if (wr_valid) begin
      mem[wr_ptr] <= wr_data_i;
    end
  end

  // Read data output - registered
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      rd_data_o <= '0;
    end else if (rd_valid) begin
      rd_data_o <= mem[rd_ptr];
    end
  end

  // FIFO control logic
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      wr_ptr <= '0;
      rd_ptr <= '0;
      count <= '0;
      overflow_o <= 1'b0;
      underflow_o <= 1'b0;
    end else begin
      // Default values for error flags
      overflow_o <= 1'b0;
      underflow_o <= 1'b0;
      
      // Handle write operation
      if (wr_en_i) begin
        if (!full_o) begin
          wr_ptr <= (wr_ptr == FIFO_DEPTH - 1) ? '0 : wr_ptr + 1'b1;
        end else begin
          overflow_o <= 1'b1;
        end
      end
      
      // Handle read operation
      if (rd_en_i) begin
        if (!empty_o) begin
          rd_ptr <= (rd_ptr == FIFO_DEPTH - 1) ? '0 : rd_ptr + 1'b1;
        end else begin
          underflow_o <= 1'b1;
        end
      end
      
      // Update count based on operations
      case ({wr_valid, rd_valid})
        2'b10: count <= count + 1'b1; // Write only
        2'b01: count <= count - 1'b1; // Read only
        2'b11: count <= count;        // Both read and write
        default: count <= count;      // No operation
      endcase
    end
  end

endmodule : rrfifo 