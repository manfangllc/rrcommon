/**
 * Testbench for the RRFIFO module
 * 
 * This testbench performs various tests on the FIFO:
 * 1. Reset verification
 * 2. Basic write/read operations
 * 3. Full/empty flag testing
 * 4. Almost full/empty threshold testing
 * 5. Overflow/underflow detection
 * 6. Back-to-back operations
 */
module rrfifo_tb;

  // Testbench parameters
  localparam int DATA_WIDTH    = 8;
  localparam int FIFO_DEPTH    = 16;
  localparam int ALMOST_FULL   = 12;
  localparam int ALMOST_EMPTY  = 4;
  localparam int CLK_PERIOD    = 10; // 10ns = 100MHz
  
  // Clock and reset
  logic clk;
  logic rst_n;
  
  // Write interface
  logic                  wr_en_i;
  logic [DATA_WIDTH-1:0] wr_data_i;
  logic                  full_o;
  logic                  almost_full_o;
  logic                  overflow_o;
  
  // Read interface
  logic                  rd_en_i;
  logic [DATA_WIDTH-1:0] rd_data_o;
  logic                  empty_o;
  logic                  almost_empty_o;
  logic                  underflow_o;
  
  // Status
  logic [$clog2(FIFO_DEPTH):0] level_o;
  
  // Testbench variables
  int error_count;
  logic [DATA_WIDTH-1:0] expected_data[$];
  
  // DUT instantiation
  rrfifo #(
    .DATA_WIDTH   (DATA_WIDTH),
    .FIFO_DEPTH   (FIFO_DEPTH),
    .ALMOST_FULL  (ALMOST_FULL),
    .ALMOST_EMPTY (ALMOST_EMPTY)
  ) dut (
    .clk           (clk),
    .rst_n         (rst_n),
    
    .wr_en_i       (wr_en_i),
    .wr_data_i     (wr_data_i),
    .full_o        (full_o),
    .almost_full_o (almost_full_o),
    .overflow_o    (overflow_o),
    
    .rd_en_i       (rd_en_i),
    .rd_data_o     (rd_data_o),
    .empty_o       (empty_o),
    .almost_empty_o(almost_empty_o),
    .underflow_o   (underflow_o),
    
    .level_o       (level_o)
  );
  
  // Clock generation
  initial begin
    clk = 0;
    forever #(CLK_PERIOD/2) clk = ~clk;
  end
  
  // Test sequence
  initial begin
    // Initialize signals and error counter
    error_count = 0;
    wr_en_i = 0;
    rd_en_i = 0;
    wr_data_i = 0;
    expected_data = {};
    
    // Reset sequence
    rst_n = 0;
    #(CLK_PERIOD*5);
    rst_n = 1;
    #(CLK_PERIOD);
    
    // Display test start message
    $display("Starting FIFO testbench...");
    
    // Test 1: Verify reset state
    verify_reset_state();
    
    // Test 2: Basic write then read operations
    basic_write_read_test();
    
    // Test 3: Fill to full then empty
    fill_empty_test();
    
    // Test 4: Test almost full/empty thresholds
    threshold_test();
    
    // Test 5: Test overflow protection
    overflow_test();
    
    // Test 6: Test underflow protection
    underflow_test();
    
    // Test 7: Concurrent read/write operations
    concurrent_rw_test();
    
    // Display test results
    if (error_count == 0) begin
      $display("All tests PASSED!");
    end else begin
      $display("Tests FAILED with %0d errors!", error_count);
    end
    
    // End simulation
    $finish;
  end
  
  // Task: Verify reset state
  task verify_reset_state();
    $display("Test 1: Verifying reset state...");
    
    if (!empty_o || full_o || almost_full_o || !almost_empty_o) begin
      $error("Reset state verification failed: Status flags incorrect!");
      error_count++;
    end
    
    if (overflow_o || underflow_o) begin
      $error("Reset state verification failed: Error flags asserted!");
      error_count++;
    end
    
    if (level_o != 0) begin
      $error("Reset state verification failed: Level not zeroed! Level: %0d", level_o);
      error_count++;
    }
    
    $display("Reset state verification complete");
  endtask
  
  // Task: Basic write then read operations
  task basic_write_read_test();
    logic [DATA_WIDTH-1:0] test_data;
    
    $display("Test 2: Basic write/read operations...");
    
    // Write 5 values
    for (int i = 0; i < 5; i++) begin
      @(posedge clk);
      test_data = $urandom_range(0, 2**DATA_WIDTH-1);
      wr_data_i = test_data;
      wr_en_i = 1;
      expected_data.push_back(test_data);
      @(posedge clk);
      wr_en_i = 0;
      
      // Check that level increases
      if (level_o != i+1) begin
        $error("Level incorrect after write %0d: Expected %0d, got %0d", i, i+1, level_o);
        error_count++;
      end
    end
    
    // Read back 5 values
    for (int i = 0; i < 5; i++) begin
      @(posedge clk);
      rd_en_i = 1;
      @(posedge clk);
      rd_en_i = 0;
      
      // Check read data
      test_data = expected_data.pop_front();
      if (rd_data_o !== test_data) begin
        $error("Read data mismatch at index %0d: Expected %h, got %h", i, test_data, rd_data_o);
        error_count++;
      end
      
      // Check that level decreases
      if (level_o != 4-i) begin
        $error("Level incorrect after read %0d: Expected %0d, got %0d", i, 4-i, level_o);
        error_count++;
      end
    end
    
    $display("Basic write/read test complete");
  endtask
  
  // Task: Fill to full then empty
  task fill_empty_test();
    logic [DATA_WIDTH-1:0] test_data;
    
    $display("Test 3: Fill to full then empty...");
    
    // Clear expected data
    expected_data = {};
    
    // Fill the FIFO
    for (int i = 0; i < FIFO_DEPTH; i++) begin
      @(posedge clk);
      test_data = $urandom_range(0, 2**DATA_WIDTH-1);
      wr_data_i = test_data;
      wr_en_i = 1;
      expected_data.push_back(test_data);
      
      // Check full flag on last write
      if (i == FIFO_DEPTH-1) begin
        @(posedge clk);
        if (!full_o) begin
          $error("Full flag not asserted when FIFO is full!");
          error_count++;
        end
      end
    end
    
    // Stop writing
    @(posedge clk);
    wr_en_i = 0;
    
    // Empty the FIFO
    for (int i = 0; i < FIFO_DEPTH; i++) begin
      @(posedge clk);
      rd_en_i = 1;
      
      // Verify read data
      if (i > 0) begin
        test_data = expected_data.pop_front();
        if (rd_data_o !== test_data) begin
          $error("Read data mismatch during emptying at index %0d: Expected %h, got %h", 
                  i-1, test_data, rd_data_o);
          error_count++;
        end
      end
      
      // Check empty flag on last read
      if (i == FIFO_DEPTH-1) begin
        @(posedge clk);
        if (!empty_o) begin
          $error("Empty flag not asserted when FIFO is empty!");
          error_count++;
        end
      end
    end
    
    // Stop reading
    @(posedge clk);
    rd_en_i = 0;
    
    $display("Fill/empty test complete");
  endtask
  
  // Task: Test almost full/empty thresholds
  task threshold_test();
    logic [DATA_WIDTH-1:0] test_data;
    
    $display("Test 4: Almost full/empty threshold testing...");
    
    // Start from empty
    if (!empty_o) begin
      $error("FIFO should be empty at start of threshold test!");
      error_count++;
    end
    
    // Fill to just below almost_full threshold
    for (int i = 0; i < ALMOST_FULL-1; i++) begin
      @(posedge clk);
      test_data = $urandom_range(0, 2**DATA_WIDTH-1);
      wr_data_i = test_data;
      wr_en_i = 1;
    end
    
    // Check that almost_full is not asserted yet
    @(posedge clk);
    wr_en_i = 0;
    if (almost_full_o) begin
      $error("Almost full flag asserted too early! Level: %0d, Threshold: %0d", 
              level_o, ALMOST_FULL);
      error_count++;
    end
    
    // Write one more to cross the threshold
    @(posedge clk);
    test_data = $urandom_range(0, 2**DATA_WIDTH-1);
    wr_data_i = test_data;
    wr_en_i = 1;
    
    // Check that almost_full is now asserted
    @(posedge clk);
    wr_en_i = 0;
    if (!almost_full_o) begin
      $error("Almost full flag not asserted when level (%0d) >= threshold (%0d)!", 
              level_o, ALMOST_FULL);
      error_count++;
    end
    
    // Now read until just above almost_empty threshold
    for (int i = 0; i < level_o - ALMOST_EMPTY - 1; i++) begin
      @(posedge clk);
      rd_en_i = 1;
      @(posedge clk);
      rd_en_i = 0;
    end
    
    // Check that almost_empty is not asserted yet
    if (almost_empty_o) begin
      $error("Almost empty flag asserted too early! Level: %0d, Threshold: %0d", 
              level_o, ALMOST_EMPTY);
      error_count++;
    end
    
    // Read one more to cross the threshold
    @(posedge clk);
    rd_en_i = 1;
    
    // Check that almost_empty is now asserted
    @(posedge clk);
    rd_en_i = 0;
    if (!almost_empty_o) begin
      $error("Almost empty flag not asserted when level (%0d) <= threshold (%0d)!", 
              level_o, ALMOST_EMPTY);
      error_count++;
    end
    
    // Read the rest to empty the FIFO
    while (!empty_o) begin
      @(posedge clk);
      rd_en_i = 1;
      @(posedge clk);
      rd_en_i = 0;
    end
    
    $display("Threshold test complete");
  endtask
  
  // Task: Test overflow protection
  task overflow_test();
    $display("Test 5: Overflow protection testing...");
    
    // Start from empty
    if (!empty_o) begin
      $error("FIFO should be empty at start of overflow test!");
      error_count++;
    end
    
    // Fill the FIFO completely
    for (int i = 0; i < FIFO_DEPTH; i++) begin
      @(posedge clk);
      wr_data_i = i;
      wr_en_i = 1;
    end
    
    // Check that FIFO is full
    @(posedge clk);
    wr_en_i = 0;
    if (!full_o) begin
      $error("FIFO should be full!");
      error_count++;
    end
    
    // Try to write one more (should cause overflow)
    @(posedge clk);
    wr_data_i = 8'hAA;
    wr_en_i = 1;
    
    // Check that overflow is detected
    @(posedge clk);
    wr_en_i = 0;
    if (!overflow_o) begin
      $error("Overflow flag not asserted when writing to full FIFO!");
      error_count++;
    end
    
    // Check that FIFO level didn't change
    if (level_o != FIFO_DEPTH) begin
      $error("FIFO level changed after overflow! Expected %0d, got %0d", 
              FIFO_DEPTH, level_o);
      error_count++;
    end
    
    // Empty the FIFO
    while (!empty_o) begin
      @(posedge clk);
      rd_en_i = 1;
      @(posedge clk);
      rd_en_i = 0;
    end
    
    $display("Overflow test complete");
  endtask
  
  // Task: Test underflow protection
  task underflow_test();
    $display("Test 6: Underflow protection testing...");
    
    // Start from empty
    if (!empty_o) begin
      $error("FIFO should be empty at start of underflow test!");
      error_count++;
    end
    
    // Try to read (should cause underflow)
    @(posedge clk);
    rd_en_i = 1;
    
    // Check that underflow is detected
    @(posedge clk);
    rd_en_i = 0;
    if (!underflow_o) begin
      $error("Underflow flag not asserted when reading from empty FIFO!");
      error_count++;
    end
    
    $display("Underflow test complete");
  endtask
  
  // Task: Concurrent read/write operations
  task concurrent_rw_test();
    logic [DATA_WIDTH-1:0] test_data[$];
    logic [DATA_WIDTH-1:0] current_data;
    
    $display("Test 7: Concurrent read/write operations...");
    
    // Start from empty
    if (!empty_o) begin
      $error("FIFO should be empty at start of concurrent R/W test!");
      error_count++;
    end
    
    // Half-fill the FIFO first
    for (int i = 0; i < FIFO_DEPTH/2; i++) begin
      @(posedge clk);
      current_data = $urandom_range(0, 2**DATA_WIDTH-1);
      wr_data_i = current_data;
      wr_en_i = 1;
      test_data.push_back(current_data);
      @(posedge clk);
      wr_en_i = 0;
    end
    
    // Now do concurrent read/write for a while
    for (int i = 0; i < 20; i++) begin
      @(posedge clk);
      current_data = $urandom_range(0, 2**DATA_WIDTH-1);
      wr_data_i = current_data;
      wr_en_i = 1;
      rd_en_i = 1;
      test_data.push_back(current_data);
      
      // Check read data (after the first cycle)
      if (i > 0) begin
        current_data = test_data.pop_front();
        if (rd_data_o !== current_data) begin
          $error("Read data mismatch during concurrent R/W: Expected %h, got %h", 
                  current_data, rd_data_o);
          error_count++;
        end
      end
    end
    
    // Stop operations
    @(posedge clk);
    wr_en_i = 0;
    rd_en_i = 0;
    
    // Check one more read value
    @(posedge clk);
    rd_en_i = 1;
    @(posedge clk);
    rd_en_i = 0;
    current_data = test_data.pop_front();
    if (rd_data_o !== current_data) begin
      $error("Final read data mismatch: Expected %h, got %h", 
              current_data, rd_data_o);
      error_count++;
    end
    
    // Empty the FIFO
    while (!empty_o) begin
      @(posedge clk);
      rd_en_i = 1;
      @(posedge clk);
      rd_en_i = 0;
    end
    
    $display("Concurrent R/W test complete");
  endtask

endmodule : rrfifo_tb 