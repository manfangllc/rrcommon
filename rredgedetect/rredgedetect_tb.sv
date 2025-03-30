// RR Common Library: Edge Detector Module Testbench
// Tests the functionality of the rredgedetect module
// Author: Claude AI

`timescale 1ns/1ps

module rredgedetect_tb();

  // Parameters
  localparam CLK_PERIOD = 10;  // 10ns = 100MHz
  localparam WIDTH = 4;        // Test with a 4-bit signal

  // Clock and reset
  logic clk;
  logic rst_n;
  
  // Signal to create edge transitions
  logic [WIDTH-1:0] signal;
  
  // Output signals
  logic [WIDTH-1:0] rise_detected;
  logic [WIDTH-1:0] fall_detected;
  logic [WIDTH-1:0] toggle_detected;
  
  // Expected output values for checking
  logic [WIDTH-1:0] expected_rise;
  logic [WIDTH-1:0] expected_fall;
  logic [WIDTH-1:0] expected_toggle;
  
  // Error tracking
  int error_count = 0;
  
  // Instantiate the edge detector
  rredgedetect #(
    .WIDTH(WIDTH)
  ) DUT (
    .clk_i(clk),
    .rst_n_i(rst_n),
    .signal_i(signal),
    .rise_o(rise_detected),
    .fall_o(fall_detected),
    .toggle_o(toggle_detected)
  );
  
  // Clock generation
  always begin
    clk = 1'b0;
    #(CLK_PERIOD/2);
    clk = 1'b1;
    #(CLK_PERIOD/2);
  end
  
  // Record previous signal value for edge detection validation
  logic [WIDTH-1:0] signal_prev;
  
  always @(posedge clk) begin
    signal_prev <= signal;
  end
  
  // Test case helper task
  task check_outputs();
    // Calculate expected outputs
    expected_rise   = signal & ~signal_prev;
    expected_fall   = ~signal & signal_prev;
    expected_toggle = signal ^ signal_prev;
    
    // Check if detector outputs match expectations
    if (rise_detected !== expected_rise) begin
      $display("ERROR at time %0t: Rising edge mismatch. Expected: %b, Got: %b", 
               $time, expected_rise, rise_detected);
      error_count++;
    end
    
    if (fall_detected !== expected_fall) begin
      $display("ERROR at time %0t: Falling edge mismatch. Expected: %b, Got: %b", 
               $time, expected_fall, fall_detected);
      error_count++;
    end
    
    if (toggle_detected !== expected_toggle) begin
      $display("ERROR at time %0t: Toggle mismatch. Expected: %b, Got: %b", 
               $time, expected_toggle, toggle_detected);
      error_count++;
    end
  endtask
  
  // Apply stimulus and check results
  initial begin
    // Initialize
    rst_n = 1'b0;
    signal = '0;
    
    // Apply reset
    #(CLK_PERIOD * 2);
    rst_n = 1'b1;
    #(CLK_PERIOD);
    
    // Test 1: Single bit toggle
    $display("Test 1: Single bit toggle");
    signal = 4'b0001;
    #(CLK_PERIOD);
    check_outputs();
    
    signal = 4'b0000;
    #(CLK_PERIOD);
    check_outputs();
    
    // Test 2: Multiple bit toggle
    $display("Test 2: Multiple bit toggle");
    signal = 4'b1010;
    #(CLK_PERIOD);
    check_outputs();
    
    signal = 4'b0101;
    #(CLK_PERIOD);
    check_outputs();
    
    // Test 3: All bits rising
    $display("Test 3: All bits rising");
    signal = 4'b0000;
    #(CLK_PERIOD);
    signal = 4'b1111;
    #(CLK_PERIOD);
    check_outputs();
    
    // Test 4: All bits falling
    $display("Test 4: All bits falling");
    signal = 4'b0000;
    #(CLK_PERIOD);
    check_outputs();
    
    // Test 5: Random transitions
    $display("Test 5: Random transitions");
    for (int i = 0; i < 20; i++) begin
      signal = $urandom;
      #(CLK_PERIOD);
      check_outputs();
    end
    
    // Finish test
    if (error_count == 0) begin
      $display("All tests PASSED!");
    end else begin
      $display("Tests FAILED with %d errors", error_count);
    end
    
    $finish;
  end
  
  // Monitoring for debug
  initial begin
    $monitor("Time: %t | Signal: %b | Rise: %b | Fall: %b | Toggle: %b", 
             $time, signal, rise_detected, fall_detected, toggle_detected);
  end
  
endmodule 