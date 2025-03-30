/**
 * Testbench for the AXI-compatible FIFO module
 * 
 * This testbench performs various tests on the AXI FIFO:
 * 1. Reset verification
 * 2. AXI write/read handshaking
 * 3. Back-to-back transactions
 * 4. Stalled reads/writes
 * 5. Full/empty flag testing
 * 6. Almost full/empty threshold testing
 * 7. Overflow/underflow detection
 */
module rrfifo_axi_tb;

  // Testbench parameters
  localparam int DATA_WIDTH    = 32;
  localparam int FIFO_DEPTH    = 16;
  localparam int ALMOST_FULL   = 12;
  localparam int ALMOST_EMPTY  = 4;
  localparam int CLK_PERIOD    = 10; // 10ns = 100MHz
  
  // Clock and reset
  logic clk;
  logic rst_n;
  
  // AXI-style write interface
  logic                  s_valid_i;
  logic                  s_ready_o;
  logic [DATA_WIDTH-1:0] s_data_i;
  
  // AXI-style read interface
  logic                  m_valid_o;
  logic                  m_ready_i;
  logic [DATA_WIDTH-1:0] m_data_o;
  
  // Status signals
  logic                  full_o;
  logic                  almost_full_o;
  logic                  empty_o;
  logic                  almost_empty_o;
  logic                  overflow_o;
  logic                  underflow_o;
  logic [$clog2(FIFO_DEPTH):0] level_o;
  
  // Testbench variables
  int error_count;
  logic [DATA_WIDTH-1:0] expected_data[$];
  
  // DUT instantiation
  rrfifo_axi #(
    .DATA_WIDTH   (DATA_WIDTH),
    .FIFO_DEPTH   (FIFO_DEPTH),
    .ALMOST_FULL  (ALMOST_FULL),
    .ALMOST_EMPTY (ALMOST_EMPTY)
  ) dut (
    .clk           (clk),
    .rst_n         (rst_n),
    
    .s_valid_i     (s_valid_i),
    .s_ready_o     (s_ready_o),
    .s_data_i      (s_data_i),
    
    .m_valid_o     (m_valid_o),
    .m_ready_i     (m_ready_i),
    .m_data_o      (m_data_o),
    
    .full_o        (full_o),
    .almost_full_o (almost_full_o),
    .empty_o       (empty_o),
    .almost_empty_o(almost_empty_o),
    .overflow_o    (overflow_o),
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
    s_valid_i = 0;
    m_ready_i = 0;
    s_data_i = 0;
    expected_data = {};
    
    // Reset sequence
    rst_n = 0;
    #(CLK_PERIOD*5);
    rst_n = 1;
    #(CLK_PERIOD);
    
    // Display test start message
    $display("Starting AXI FIFO testbench...");
    
    // Test 1: Verify reset state
    verify_reset_state();
    
    // Test 2: Basic AXI write then read operations
    basic_axi_write_read();
    
    // Test 3: Fill to full then empty
    fill_empty_test();
    
    // Test 4: Test almost full/empty thresholds
    threshold_test();
    
    // Test 5: Test stalled writes
    stalled_writes_test();
    
    // Test 6: Test stalled reads
    stalled_reads_test();
    
    // Test 7: Test overflow protection
    overflow_test();
    
    // Test 8: Test underflow protection
    underflow_test();
    
    // Test 9: Test back-to-back transactions
    back_to_back_test();
    
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
    end
    
    if (!s_ready_o || m_valid_o) begin
      $error("Reset state verification failed: AXI handshaking signals incorrect!");
      error_count++;
    end
    
    $display("Reset state verification complete");
  endtask
  
  // Task: Basic AXI write and read operations
  task basic_axi_write_read();
    logic [DATA_WIDTH-1:0] test_data;
    
    $display("Test 2: Basic AXI write/read operations...");
    
    // Write 5 values using AXI handshaking
    for (int i = 0; i < 5; i++) begin
      test_data = $urandom_range(0, 2**DATA_WIDTH-1);
      
      // Start transaction
      @(posedge clk);
      s_data_i = test_data;
      s_valid_i = 1;
      
      // Wait for ready
      wait(s_ready_o);
      @(posedge clk);
      
      // Transaction complete
      s_valid_i = 0;
      expected_data.push_back(test_data);
      
      // Check level
      if (level_o != i+1) begin
        $error("Level incorrect after write %0d: Expected %0d, got %0d", i, i+1, level_o);
        error_count++;
      end
    end
    
    // Read back 5 values using AXI handshaking
    for (int i = 0; i < 5; i++) begin
      // Assert ready
      @(posedge clk);
      m_ready_i = 1;
      
      // Wait for valid data
      wait(m_valid_o);
      @(posedge clk);
      
      // Check read data
      test_data = expected_data.pop_front();
      if (m_data_o !== test_data) begin
        $error("Read data mismatch at index %0d: Expected %h, got %h", i, test_data, m_data_o);
        error_count++;
      end
      
      // Transaction complete
      m_ready_i = 0;
      
      // Check level
      if (level_o != 4-i) begin
        $error("Level incorrect after read %0d: Expected %0d, got %0d", i, 4-i, level_o);
        error_count++;
      end
    end
    
    $display("Basic AXI write/read test complete");
  endtask
  
  // Task: Fill to full then empty
  task fill_empty_test();
    logic [DATA_WIDTH-1:0] test_data;
    
    $display("Test 3: Fill to full then empty...");
    
    // Clear expected data
    expected_data = {};
    
    // Fill the FIFO
    for (int i = 0; i < FIFO_DEPTH; i++) begin
      test_data = $urandom_range(0, 2**DATA_WIDTH-1);
      
      // Start transaction
      @(posedge clk);
      s_data_i = test_data;
      s_valid_i = 1;
      
      // Wait for ready
      wait(s_ready_o);
      @(posedge clk);
      
      expected_data.push_back(test_data);
      
      // Last write should make FIFO full
      if (i == FIFO_DEPTH-1) begin
        if (!full_o) begin
          $error("FIFO should be full after %0d writes!", FIFO_DEPTH);
          error_count++;
        end
        
        // Ready should be deasserted when full
        if (s_ready_o) begin
          $error("s_ready_o should be deasserted when FIFO is full!");
          error_count++;
        end
      end
    end
    
    // Stop writing
    @(posedge clk);
    s_valid_i = 0;
    
    // Empty the FIFO
    m_ready_i = 1;
    
    for (int i = 0; i < FIFO_DEPTH; i++) begin
      // Wait for valid data
      wait(m_valid_o);
      @(posedge clk);
      
      // Check read data
      test_data = expected_data.pop_front();
      if (m_data_o !== test_data) begin
        $error("Read data mismatch during emptying at index %0d: Expected %h, got %h", 
                i, test_data, m_data_o);
        error_count++;
      end
      
      // Last read should make FIFO empty
      if (i == FIFO_DEPTH-1) begin
        if (!empty_o) begin
          $error("FIFO should be empty after %0d reads!", FIFO_DEPTH);
          error_count++;
        end
        
        // Valid should be deasserted when empty
        if (m_valid_o) begin
          $error("m_valid_o should be deasserted when FIFO is empty!");
          error_count++;
        end
      end
    end
    
    // Stop reading
    @(posedge clk);
    m_ready_i = 0;
    
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
      test_data = $urandom_range(0, 2**DATA_WIDTH-1);
      
      // Write transaction
      @(posedge clk);
      s_data_i = test_data;
      s_valid_i = 1;
      
      wait(s_ready_o);
      @(posedge clk);
      s_valid_i = 0;
    end
    
    // Check that almost_full is not asserted yet
    if (almost_full_o) begin
      $error("Almost full flag asserted too early! Level: %0d, Threshold: %0d", 
              level_o, ALMOST_FULL);
      error_count++;
    end
    
    // Write one more to cross the threshold
    test_data = $urandom_range(0, 2**DATA_WIDTH-1);
    @(posedge clk);
    s_data_i = test_data;
    s_valid_i = 1;
    
    wait(s_ready_o);
    @(posedge clk);
    s_valid_i = 0;
    
    // Check that almost_full is now asserted
    if (!almost_full_o) begin
      $error("Almost full flag not asserted when level (%0d) >= threshold (%0d)!", 
              level_o, ALMOST_FULL);
      error_count++;
    end
    
    // Now read until just above almost_empty threshold
    m_ready_i = 1;
    
    // Wait until we're at ALMOST_EMPTY + 1
    while (level_o > ALMOST_EMPTY + 1) begin
      @(posedge clk);
    end
    
    m_ready_i = 0;
    
    // Check that almost_empty is not asserted yet
    if (almost_empty_o) begin
      $error("Almost empty flag asserted too early! Level: %0d, Threshold: %0d", 
              level_o, ALMOST_EMPTY);
      error_count++;
    end
    
    // Read one more to cross the threshold
    @(posedge clk);
    m_ready_i = 1;
    
    wait(m_valid_o);
    @(posedge clk);
    m_ready_i = 0;
    
    // Check that almost_empty is now asserted
    if (!almost_empty_o) begin
      $error("Almost empty flag not asserted when level (%0d) <= threshold (%0d)!", 
              level_o, ALMOST_EMPTY);
      error_count++;
    end
    
    // Read the rest to empty the FIFO
    m_ready_i = 1;
    while (!empty_o) begin
      @(posedge clk);
    end
    m_ready_i = 0;
    
    $display("Threshold test complete");
  endtask
  
  // Task: Test stalled writes (valid without ready)
  task stalled_writes_test();
    logic [DATA_WIDTH-1:0] test_data;
    
    $display("Test 5: Stalled writes testing...");
    
    // Start from empty
    if (!empty_o) begin
      $error("FIFO should be empty at start of stalled writes test!");
      error_count++;
    end
    
    // Fill FIFO completely to force s_ready_o to deassert
    for (int i = 0; i < FIFO_DEPTH; i++) begin
      test_data = $urandom_range(0, 2**DATA_WIDTH-1);
      
      @(posedge clk);
      s_data_i = test_data;
      s_valid_i = 1;
      
      wait(s_ready_o);
      @(posedge clk);
      
      expected_data.push_back(test_data);
    end
    
    // FIFO should be full now
    if (!full_o || s_ready_o) begin
      $error("FIFO should be full and s_ready_o should be low after filling!");
      error_count++;
    end
    
    // Keep valid high while ready is low (stalled write)
    test_data = $urandom_range(0, 2**DATA_WIDTH-1);
    s_data_i = test_data;
    s_valid_i = 1;
    
    // Count how many cycles we're stalled
    int stall_cycles = 0;
    while (!s_ready_o && stall_cycles < 5) begin
      @(posedge clk);
      stall_cycles++;
    end
    
    // Verify stalled for some time
    if (stall_cycles == 0) begin
      $error("Write wasn't stalled when FIFO was full!");
      error_count++;
    end
    
    // Read one item to make space
    m_ready_i = 1;
    wait(m_valid_o);
    @(posedge clk);
    m_ready_i = 0;
    
    // After reading, s_ready_o should be high again
    if (!s_ready_o) begin
      $error("s_ready_o didn't reassert after making space in FIFO!");
      error_count++;
    end
    
    // The stalled write should complete now
    @(posedge clk);
    s_valid_i = 0;
    expected_data.push_back(test_data);
    
    // Empty the FIFO
    m_ready_i = 1;
    while (!empty_o) begin
      @(posedge clk);
    end
    m_ready_i = 0;
    
    $display("Stalled writes test complete");
  endtask
  
  // Task: Test stalled reads (ready without valid)
  task stalled_reads_test();
    $display("Test 6: Stalled reads testing...");
    
    // Start from empty
    if (!empty_o) begin
      $error("FIFO should be empty at start of stalled reads test!");
      error_count++;
    end
    
    // Attempt read when empty (ready without valid)
    m_ready_i = 1;
    
    // Count how many cycles we're stalled
    int stall_cycles = 0;
    while (!m_valid_o && stall_cycles < 5) begin
      @(posedge clk);
      stall_cycles++;
    end
    
    // Verify stalled for some time
    if (stall_cycles == 0) begin
      $error("Read wasn't stalled when FIFO was empty!");
      error_count++;
    end
    
    // Write one item
    logic [DATA_WIDTH-1:0] test_data = $urandom_range(0, 2**DATA_WIDTH-1);
    s_data_i = test_data;
    s_valid_i = 1;
    
    wait(s_ready_o);
    @(posedge clk);
    s_valid_i = 0;
    
    // The stalled read should complete now
    wait(m_valid_o);
    @(posedge clk);
    
    // Check data
    if (m_data_o !== test_data) begin
      $error("Data mismatch after stalled read: Expected %h, got %h", 
              test_data, m_data_o);
      error_count++;
    end
    
    m_ready_i = 0;
    
    $display("Stalled reads test complete");
  endtask
  
  // Task: Test overflow protection
  task overflow_test();
    $display("Test 7: Overflow protection testing...");
    
    // Start from empty
    if (!empty_o) begin
      $error("FIFO should be empty at start of overflow test!");
      error_count++;
    end
    
    // Fill the FIFO completely
    for (int i = 0; i < FIFO_DEPTH; i++) begin
      @(posedge clk);
      s_data_i = i;
      s_valid_i = 1;
      
      wait(s_ready_o);
      @(posedge clk);
    end
    
    // Keep valid high after FIFO is full (should cause overflow)
    s_valid_i = 1;
    s_data_i = 32'hDEADBEEF;
    
    // Wait a few cycles
    repeat(3) @(posedge clk);
    
    // Check that overflow is detected
    if (!overflow_o) begin
      $error("Overflow flag not asserted when writing to full FIFO!");
      error_count++;
    end
    
    // Stop writing
    s_valid_i = 0;
    
    // Empty the FIFO
    m_ready_i = 1;
    while (!empty_o) begin
      @(posedge clk);
    end
    m_ready_i = 0;
    
    $display("Overflow test complete");
  endtask
  
  // Task: Test underflow protection
  task underflow_test();
    $display("Test 8: Underflow protection testing...");
    
    // Start from empty
    if (!empty_o) begin
      $error("FIFO should be empty at start of underflow test!");
      error_count++;
    end
    
    // Keep ready high when FIFO is empty (should cause underflow)
    m_ready_i = 1;
    
    // Wait a few cycles
    repeat(3) @(posedge clk);
    
    // Check that underflow is detected
    if (!underflow_o) begin
      $error("Underflow flag not asserted when reading from empty FIFO!");
      error_count++;
    end
    
    // Stop reading
    m_ready_i = 0;
    
    $display("Underflow test complete");
  endtask
  
  // Task: Test back-to-back transactions
  task back_to_back_test();
    logic [DATA_WIDTH-1:0] test_data[$];
    logic [DATA_WIDTH-1:0] current_data;
    
    $display("Test 9: Back-to-back transactions testing...");
    
    // Start from empty
    if (!empty_o) begin
      $error("FIFO should be empty at start of back-to-back test!");
      error_count++;
    end
    
    // Continuously write and read for 20 cycles
    s_valid_i = 1;
    m_ready_i = 1;
    
    for (int i = 0; i < 20; i++) begin
      current_data = $urandom_range(0, 2**DATA_WIDTH-1);
      s_data_i = current_data;
      test_data.push_back(current_data);
      @(posedge clk);
      
      // Skip first few reads as the FIFO needs to fill first
      if (i > 1 && m_valid_o) begin
        current_data = test_data.pop_front();
        if (m_data_o !== current_data) begin
          $error("Read data mismatch during back-to-back: Expected %h, got %h", 
                  current_data, m_data_o);
          error_count++;
        end
      end
    end
    
    // Stop operations
    s_valid_i = 0;
    
    // Continue reading until empty
    while (!empty_o) begin
      @(posedge clk);
    end
    
    m_ready_i = 0;
    
    $display("Back-to-back test complete");
  endtask

endmodule : rrfifo_axi_tb 