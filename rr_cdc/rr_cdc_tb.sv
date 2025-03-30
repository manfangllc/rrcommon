// RR Common Library: Clock Domain Crossing Module Testbench
// Tests the functionality of the rr_cdc module in all modes
// Author: Claude AI

`timescale 1ns/1ps

module rr_cdc_tb();

  // Parameters
  localparam DATA_WIDTH = 8;           // Width of test data
  localparam SYNC_STAGES = 2;          // Synchronizer stages
  localparam CLK_SRC_PERIOD = 10;      // 10ns = 100MHz
  localparam CLK_DST_PERIOD = 15;      // 15ns = ~66.67MHz (intentionally different)
  localparam NUM_TRANSFERS = 10;       // Number of test data transfers
  
  // Test control
  string current_test = "INIT";        // Current test mode
  int error_count = 0;                 // Error counter
  int transfer_count = 0;              // Transfer counter
  
  // Shared signals
  logic [DATA_WIDTH-1:0] data_src;     // Source data input
  logic valid_src;                     // Source valid signal
  logic ready_src;                     // Source ready signal
  logic [DATA_WIDTH-1:0] data_dst;     // Destination data output
  logic valid_dst;                     // Destination valid signal
  logic ready_dst;                     // Destination ready signal
  
  // Clock and reset signals
  logic clk_src;                       // Source clock
  logic clk_dst;                       // Destination clock
  logic rst_src_n;                     // Source reset (active low)
  logic rst_dst_n;                     // Destination reset (active low)
  
  // Expected data for verification
  logic [DATA_WIDTH-1:0] expected_data [NUM_TRANSFERS-1:0];
  logic [DATA_WIDTH-1:0] received_data [NUM_TRANSFERS-1:0];
  
  // Clock generation
  initial begin
    clk_src = 1'b0;
    forever #(CLK_SRC_PERIOD/2) clk_src = ~clk_src;
  end
  
  initial begin
    clk_dst = 1'b0;
    forever #(CLK_DST_PERIOD/2) clk_dst = ~clk_dst;
  end
  
  // Test data generation
  initial begin
    for (int i = 0; i < NUM_TRANSFERS; i++) begin
      expected_data[i] = $urandom;
    end
  end
  
  // Generate module instances for each mode using generate
  // Since we want to test all modes, we'll create separate instances
  
  // PULSE mode CDC instance
  rr_cdc #(
    .WIDTH(DATA_WIDTH),
    .SYNC_STAGES(SYNC_STAGES),
    .MODE("PULSE")
  ) pulse_cdc (
    .clk_src_i(clk_src),
    .rst_src_n_i(rst_src_n),
    .data_src_i(data_src),
    .valid_src_i(valid_src),
    .ready_src_o(ready_src_pulse),
    
    .clk_dst_i(clk_dst),
    .rst_dst_n_i(rst_dst_n),
    .data_dst_o(data_dst_pulse),
    .valid_dst_o(valid_dst_pulse),
    .ready_dst_i(ready_dst)
  );
  
  // TOGGLE mode CDC instance
  rr_cdc #(
    .WIDTH(DATA_WIDTH),
    .SYNC_STAGES(SYNC_STAGES),
    .MODE("TOGGLE")
  ) toggle_cdc (
    .clk_src_i(clk_src),
    .rst_src_n_i(rst_src_n),
    .data_src_i(data_src),
    .valid_src_i(valid_src),
    .ready_src_o(ready_src_toggle),
    
    .clk_dst_i(clk_dst),
    .rst_dst_n_i(rst_dst_n),
    .data_dst_o(data_dst_toggle),
    .valid_dst_o(valid_dst_toggle),
    .ready_dst_i(ready_dst)
  );
  
  // HANDSHAKE mode CDC instance
  rr_cdc #(
    .WIDTH(DATA_WIDTH),
    .SYNC_STAGES(SYNC_STAGES),
    .MODE("HANDSHAKE")
  ) handshake_cdc (
    .clk_src_i(clk_src),
    .rst_src_n_i(rst_src_n),
    .data_src_i(data_src),
    .valid_src_i(valid_src),
    .ready_src_o(ready_src_handshake),
    
    .clk_dst_i(clk_dst),
    .rst_dst_n_i(rst_dst_n),
    .data_dst_o(data_dst_handshake),
    .valid_dst_o(valid_dst_handshake),
    .ready_dst_i(ready_dst)
  );
  
  // Mode-specific signal connections based on test mode
  always_comb begin
    case (current_test)
      "PULSE": begin
        ready_src = ready_src_pulse;
        data_dst = data_dst_pulse;
        valid_dst = valid_dst_pulse;
      end
      "TOGGLE": begin
        ready_src = ready_src_toggle;
        data_dst = data_dst_toggle;
        valid_dst = valid_dst_toggle;
      end
      "HANDSHAKE": begin
        ready_src = ready_src_handshake;
        data_dst = data_dst_handshake;
        valid_dst = valid_dst_handshake;
      end
      default: begin
        ready_src = 1'b0;
        data_dst = '0;
        valid_dst = 1'b0;
      end
    endcase
  end
  
  // Source domain driver task
  task send_data(input [DATA_WIDTH-1:0] data);
    // Wait for ready
    wait(ready_src);
    
    // Apply data and valid
    @(posedge clk_src);
    data_src <= data;
    valid_src <= 1'b1;
    
    // Wait one cycle
    @(posedge clk_src);
    valid_src <= 1'b0;
  endtask
  
  // Destination domain receiver task
  task receive_data(output [DATA_WIDTH-1:0] data);
    // Wait for valid
    wait(valid_dst);
    
    // Capture data
    data = data_dst;
    
    // Assert ready to acknowledge receipt
    @(posedge clk_dst);
    ready_dst <= 1'b1;
    
    // Wait one cycle
    @(posedge clk_dst);
    ready_dst <= 1'b0;
  endtask
  
  // Verification task
  task verify_transfer(int idx);
    if (received_data[idx] !== expected_data[idx]) begin
      $display("ERROR: Transfer %0d mismatch! Expected: 0x%h, Got: 0x%h", 
               idx, expected_data[idx], received_data[idx]);
      error_count++;
    end else begin
      $display("Transfer %0d successful: 0x%h", idx, received_data[idx]);
    end
  endtask
  
  // Main test sequence
  initial begin
    // Initial values
    rst_src_n = 1'b0;
    rst_dst_n = 1'b0;
    data_src = '0;
    valid_src = 1'b0;
    ready_dst = 1'b0;
    
    // Apply reset
    #100;
    rst_src_n = 1'b1;
    rst_dst_n = 1'b1;
    #100;
    
    // Test each mode
    foreach ({"PULSE", "TOGGLE", "HANDSHAKE"}) begin
      current_test = "";
      #10 current_test = item;  // Add delay to ensure assignment happens at deterministic time
      
      $display("\n=== Testing %s mode ===", current_test);
      
      // Reset transfer counter
      transfer_count = 0;
      
      // Start source and destination processes
      fork
        // Source process - send data transfers
        begin
          for (int i = 0; i < NUM_TRANSFERS; i++) begin
            send_data(expected_data[i]);
            
            // Add delay between transfers
            #(CLK_SRC_PERIOD * 5);
          end
        end
        
        // Destination process - receive data and verify
        begin
          for (int i = 0; i < NUM_TRANSFERS; i++) begin
            receive_data(received_data[i]);
            verify_transfer(i);
            transfer_count++;
            
            // Add delay between receives
            #(CLK_DST_PERIOD * 5);
          end
        end
      join
      
      // Ensure time for any pending activities to complete
      #500;
    end
    
    // Report results
    $display("\n=== Test Summary ===");
    if (error_count == 0) begin
      $display("All tests PASSED! Total transfers: %0d", transfer_count);
    end else begin
      $display("Tests FAILED with %0d errors out of %0d transfers", 
               error_count, transfer_count);
    end
    
    $finish;
  end
  
  // Monitor for debug
  initial begin
    $monitor("Time: %0t | Test: %s | Src Ready: %b | Dst Valid: %b | Transfer Count: %0d", 
             $time, current_test, ready_src, valid_dst, transfer_count);
  end

endmodule 