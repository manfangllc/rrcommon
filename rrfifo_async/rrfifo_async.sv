/**
 * Asynchronous (dual-clock) parameterizable FIFO
 *
 * A safe clock-domain-crossing FIFO using the classic Gray-code pointer
 * technique (Cliff Cummings style). The write and read interfaces live in
 * independent clock domains (wr_clk_i / rd_clk_i). Binary + Gray pointers are
 * maintained per domain; the Gray pointers are synchronized into the opposite
 * domain through a double-flop synchronizer (the reused `sync_chain` submodule
 * from rr_cdc.sv) and compared to derive full/empty.
 *
 * Features:
 * - Independent write/read clock domains
 * - Full / empty (Gray-compare, glitch-free) + almost_full / almost_empty
 * - Overflow / underflow protection with 1-cycle detection pulses
 * - Conservative per-domain occupancy: wr_level_o (over-counts -> safe vs
 *   overflow), rd_level_o (under-counts -> safe vs underflow)
 * - Registered, non-FWFT read (rd_data_o valid the cycle AFTER rd_en)
 * - Per-direction WR_MODE / RD_MODE: "LEVEL" (one transfer per clock while the
 *   enable is high) or "PULSE" (one rising edge of the enable = exactly one
 *   transfer; the enable must drop and rise again for the next)
 *
 * Constraints:
 * - FIFO_DEPTH must be a power of 2 and >= 2 (the Gray full/empty trick
 *   requires it). Enforced by an elaboration-time $error.
 * - RESET: wr_rst_n_i and rd_rst_n_i must be asserted together (overlapping)
 *   to reset the FIFO. Resetting only one domain leaves occupancy undefined
 *   until both have been reset. Each synchronizer uses its destination-domain
 *   reset, so a partial reset corrupts the cross-domain pointer view.
 */
module rrfifo_async #(
  parameter int    DATA_WIDTH   = 8,
  parameter int    FIFO_DEPTH   = 16,    // must be a power of 2, >= 2
  parameter int    ALMOST_FULL  = 12,
  parameter int    ALMOST_EMPTY = 4,
  parameter int    SYNC_STAGES  = 2,     // pointer synchronizer flop count
  parameter        WR_MODE      = "LEVEL", // "LEVEL" or "PULSE"
  parameter        RD_MODE      = "LEVEL", // "LEVEL" or "PULSE"
  parameter        RAM_STYLE    = "auto"   // mem inference hint: "auto"/"block"/
                                           // "distributed"/"ultra"/"registers"
) (
  // Write domain
  input  logic                        wr_clk_i,
  input  logic                        wr_rst_n_i,
  input  logic                        wr_en_i,
  input  logic [DATA_WIDTH-1:0]       wr_data_i,
  output logic                        full_o,
  output logic                        almost_full_o,
  output logic                        overflow_o,
  output logic [$clog2(FIFO_DEPTH):0] wr_level_o,

  // Read domain
  input  logic                        rd_clk_i,
  input  logic                        rd_rst_n_i,
  input  logic                        rd_en_i,
  output logic [DATA_WIDTH-1:0]       rd_data_o,
  output logic                        empty_o,
  output logic                        almost_empty_o,
  output logic                        underflow_o,
  output logic [$clog2(FIFO_DEPTH):0] rd_level_o
);

  // ------------------------------------------------------------------
  // Local parameters
  // ------------------------------------------------------------------
  localparam int ADDR_WIDTH = $clog2(FIFO_DEPTH);
  localparam int PTR_WIDTH  = ADDR_WIDTH + 1;   // extra MSB to disambiguate full/empty

  // ------------------------------------------------------------------
  // Elaboration-time sanity checks
  // ------------------------------------------------------------------
  initial begin
    if (FIFO_DEPTH < 2 || (FIFO_DEPTH & (FIFO_DEPTH - 1)) != 0)
      $error("rrfifo_async: FIFO_DEPTH must be a power of 2 and >= 2 (got %0d)", FIFO_DEPTH);
    if (ALMOST_FULL  > FIFO_DEPTH || ALMOST_FULL  < 1)
      $error("rrfifo_async: ALMOST_FULL out of range (got %0d)", ALMOST_FULL);
    if (ALMOST_EMPTY > FIFO_DEPTH || ALMOST_EMPTY < 0)
      $error("rrfifo_async: ALMOST_EMPTY out of range (got %0d)", ALMOST_EMPTY);
  end

  // ------------------------------------------------------------------
  // Storage (simple dual-port: 1 write port, 1 read port; no reset)
  // ------------------------------------------------------------------
  // ram_style is a parameterized synthesis hint (not a primitive): "auto" lets
  // Vivado pick block vs distributed by depth; pin it per-instance if needed.
  (* ram_style = RAM_STYLE *) logic [DATA_WIDTH-1:0] mem [FIFO_DEPTH-1:0];

  // ------------------------------------------------------------------
  // Pointers (binary + Gray), one set per domain
  // ------------------------------------------------------------------
  logic [PTR_WIDTH-1:0] wr_bin, wr_bin_next, wr_gray;
  logic [PTR_WIDTH-1:0] rd_bin, rd_bin_next, rd_gray;

  // Synchronized copies of the opposite domain's Gray pointer
  logic [PTR_WIDTH-1:0] wr_gray_sync;  // wr_gray sampled in the read domain
  logic [PTR_WIDTH-1:0] rd_gray_sync;  // rd_gray sampled in the write domain

  // Enable edge-detect registers (for PULSE mode)
  logic wr_en_q, rd_en_q;

  // ------------------------------------------------------------------
  // Gray <-> binary helper (Gray->binary XOR reduction)
  // ------------------------------------------------------------------
  function automatic logic [PTR_WIDTH-1:0] gray2bin(input logic [PTR_WIDTH-1:0] g);
    logic [PTR_WIDTH-1:0] b;
    for (int i = PTR_WIDTH - 1; i >= 0; i--) begin
      b[i] = ^(g >> i);
    end
    return b;
  endfunction

  // ------------------------------------------------------------------
  // Effective (mode-gated) enables
  // ------------------------------------------------------------------
  logic wr_en_eff, rd_en_eff;
  assign wr_en_eff = (WR_MODE == "PULSE") ? (wr_en_i & ~wr_en_q) : wr_en_i;
  assign rd_en_eff = (RD_MODE == "PULSE") ? (rd_en_i & ~rd_en_q) : rd_en_i;

  logic wr_valid, rd_valid;
  assign wr_valid = wr_en_eff & ~full_o;
  assign rd_valid = rd_en_eff & ~empty_o;

  assign wr_bin_next = wr_bin + 1'b1;
  assign rd_bin_next = rd_bin + 1'b1;

  // ------------------------------------------------------------------
  // Full / empty (from registered Gray pointers only)
  // ------------------------------------------------------------------
  logic [PTR_WIDTH-1:0] full_cmp;
  generate
    if (ADDR_WIDTH >= 2) begin : g_full_cmp
      // "one lap ahead": invert the top two Gray MSBs of the synced read ptr
      assign full_cmp = { ~rd_gray_sync[PTR_WIDTH-1],
                          ~rd_gray_sync[PTR_WIDTH-2],
                           rd_gray_sync[PTR_WIDTH-3:0] };
    end else begin : g_full_cmp_small
      // FIFO_DEPTH==2 (ADDR_WIDTH==1): 2-bit pointer, invert both bits
      assign full_cmp = ~rd_gray_sync;
    end
  endgenerate

  assign empty_o = (rd_gray == wr_gray_sync);
  assign full_o  = (wr_gray == full_cmp);

  // ------------------------------------------------------------------
  // Conservative per-domain occupancy levels
  // ------------------------------------------------------------------
  logic [PTR_WIDTH-1:0] rd_bin_sync, wr_bin_sync;
  assign rd_bin_sync = gray2bin(rd_gray_sync); // older read ptr, seen in wr domain
  assign wr_bin_sync = gray2bin(wr_gray_sync); // older write ptr, seen in rd domain

  assign wr_level_o     = wr_bin - rd_bin_sync; // over-count (safe vs overflow)
  assign rd_level_o     = wr_bin_sync - rd_bin; // under-count (safe vs underflow)
  assign almost_full_o  = (wr_level_o >= ALMOST_FULL);
  assign almost_empty_o = (rd_level_o <= ALMOST_EMPTY);

  // ------------------------------------------------------------------
  // Write domain
  // ------------------------------------------------------------------
  always_ff @(posedge wr_clk_i or negedge wr_rst_n_i) begin
    if (!wr_rst_n_i) begin
      wr_bin     <= '0;
      wr_gray    <= '0;
      wr_en_q    <= 1'b0;
      overflow_o <= 1'b0;
    end else begin
      wr_en_q    <= wr_en_i;
      overflow_o <= wr_en_eff & full_o; // 1-cycle pulse, default 0
      if (wr_valid) begin
        wr_bin  <= wr_bin_next;
        wr_gray <= wr_bin_next ^ (wr_bin_next >> 1);
      end
    end
  end

  // Memory write port (RAMs don't reset)
  always_ff @(posedge wr_clk_i) begin
    if (wr_valid) begin
      mem[wr_bin[ADDR_WIDTH-1:0]] <= wr_data_i;
    end
  end

  // ------------------------------------------------------------------
  // Read domain
  // ------------------------------------------------------------------
  always_ff @(posedge rd_clk_i or negedge rd_rst_n_i) begin
    if (!rd_rst_n_i) begin
      rd_bin      <= '0;
      rd_gray     <= '0;
      rd_en_q     <= 1'b0;
      underflow_o <= 1'b0;
    end else begin
      rd_en_q     <= rd_en_i;
      underflow_o <= rd_en_eff & empty_o; // 1-cycle pulse, default 0
      if (rd_valid) begin
        rd_bin  <= rd_bin_next;
        rd_gray <= rd_bin_next ^ (rd_bin_next >> 1);
      end
    end
  end

  // Registered, non-FWFT read data (read current addr BEFORE increment)
  always_ff @(posedge rd_clk_i or negedge rd_rst_n_i) begin
    if (!rd_rst_n_i) begin
      rd_data_o <= '0;
    end else if (rd_valid) begin
      rd_data_o <= mem[rd_bin[ADDR_WIDTH-1:0]];
    end
  end

  // ------------------------------------------------------------------
  // Pointer CDC: synchronize each Gray pointer into the opposite domain
  // ------------------------------------------------------------------
  sync_chain #(
    .WIDTH       (PTR_WIDTH),
    .STAGES      (SYNC_STAGES),
    .RESET_VALUE ('0)
  ) u_wr2rd (
    .clk_i   (rd_clk_i),
    .rst_n_i (rd_rst_n_i),
    .data_i  (wr_gray),
    .data_o  (wr_gray_sync)
  );

  sync_chain #(
    .WIDTH       (PTR_WIDTH),
    .STAGES      (SYNC_STAGES),
    .RESET_VALUE ('0)
  ) u_rd2wr (
    .clk_i   (wr_clk_i),
    .rst_n_i (wr_rst_n_i),
    .data_i  (rd_gray),
    .data_o  (rd_gray_sync)
  );

endmodule : rrfifo_async
