// RR Common Library: PWM Generator Module Testbench
// Tests the functionality of the rrpwm module
// Author: Claude AI

`timescale 1ns/1ps

module rrpwm_tb();

  // Parameters
  localparam CLK_PERIOD = 10;        // 10ns = 100MHz
  localparam COUNTER_WIDTH = 8;      // 8-bit counter resolution
  localparam NUM_CHANNELS = 4;       // Test with 4 channels
  
  // Clock and reset
  logic clk;
  logic rst_n;
  
  // Test control signals
  logic [COUNTER_WIDTH-1:0] period;
  logic [NUM_CHANNELS-1:0] enable;
  logic [COUNTER_WIDTH-1:0] duty[NUM_CHANNELS-1:0];
  
  // PWM outputs
  logic [NUM_CHANNELS-1:0] pwm;
  
  // Measurement variables
  int high_count[NUM_CHANNELS-1:0];   // Count of high cycles per period
  int period_count;                   // Count of total cycles per period
  real measured_duty[NUM_CHANNELS-1:0]; // Measured duty cycle ratio
  int error_count = 0;                // Error counter
  
  // Instantiate the PWM generator
  rrpwm #(
    .COUNTER_WIDTH(COUNTER_WIDTH),
    .DEFAULT_PERIOD(255),
    .DEFAULT_DUTY(128),
    .NUM_CHANNELS(NUM_CHANNELS),
    .POLARITY(1)  // Active high
  ) DUT (
    .clk_i(clk),
    .rst_n_i(rst_n),
    .period_i(period),
    .enable_i(enable),
    .duty_i(duty),
    .pwm_o(pwm)
  );
  
  // Clock generation
  initial begin
    clk = 1'b0;
    forever #(CLK_PERIOD/2) clk = ~clk;
  end
  
  // Measure period and duty cycle for each channel
  task measure_pwm(int channel, int cycles);
    // Reset counters
    high_count[channel] = 0;
    period_count = 0;
    
    // Measure for the specified number of complete periods
    for (int i = 0; i < cycles; i++) begin
      // Wait for rising edge
      wait(pwm[channel] == 1'b1);
      
      // Count through one complete period
      while (period_count < period) begin
        @(posedge clk);
        period_count++;
        if (pwm[channel] == 1'b1) begin
          high_count[channel]++;
        end
      end
      
      // Reset period counter for next cycle
      period_count = 0;
    end
    
    // Calculate measured duty cycle
    measured_duty[channel] = real'(high_count[channel]) / real'(period);
    
    // Expected duty ratio
    real expected_duty = real'(duty[channel]) / real'(period);
    
    // Check if duty cycle is within tolerance
    real tolerance = 0.01; // 1% tolerance
    if (abs(measured_duty[channel] - expected_duty) > tolerance) begin
      $display("ERROR: Channel %0d Duty cycle mismatch. Expected: %f, Measured: %f", 
               channel, expected_duty, measured_duty[channel]);
      error_count++;
    end else begin
      $display("Channel %0d duty cycle correct: %f", channel, measured_duty[channel]);
    end
  endtask
  
  // Helper function for absolute value
  function real abs(real value);
    return (value < 0) ? -value : value;
  endfunction
  
  // Main test sequence
  initial begin
    // Initialize
    rst_n = 1'b0;
    period = 100;  // Set period to 100 clock cycles
    enable = '0;   // Disable all channels
    
    for (int i = 0; i < NUM_CHANNELS; i++) begin
      duty[i] = 0;
    end
    
    // Apply reset
    @(posedge clk);
    #(CLK_PERIOD * 2);
    rst_n = 1'b1;
    #(CLK_PERIOD * 2);
    
    // Test 1: Basic operation - Enable channel 0 with 50% duty cycle
    $display("\n=== Test 1: Basic 50%% duty cycle ===");
    duty[0] = 50;  // 50% duty cycle
    enable[0] = 1'b1;
    #(CLK_PERIOD * period * 3);  // Wait 3 periods
    measure_pwm(0, 1);
    
    // Test 2: Multiple channels with different duty cycles
    $display("\n=== Test 2: Multiple channels ===");
    duty[1] = 25;   // 25% duty cycle
    duty[2] = 75;   // 75% duty cycle
    duty[3] = 10;   // 10% duty cycle
    enable = 4'b1111;  // Enable all channels
    #(CLK_PERIOD * period * 3);  // Wait 3 periods
    
    for (int i = 0; i < NUM_CHANNELS; i++) begin
      measure_pwm(i, 1);
    end
    
    // Test 3: Change duty cycle during operation
    $display("\n=== Test 3: Duty cycle updates ===");
    duty[0] = 80;   // Change to 80% duty cycle
    #(CLK_PERIOD * period * 3);  // Wait 3 periods
    measure_pwm(0, 1);
    
    // Test 4: Change period during operation
    $display("\n=== Test 4: Period change ===");
    period = 200;  // Double the period
    duty[0] = 100;  // Set to 50% of new period
    #(CLK_PERIOD * period * 3);  // Wait 3 periods
    measure_pwm(0, 1);
    
    // Test 5: Test enable/disable functionality
    $display("\n=== Test 5: Enable/disable ===");
    enable = 4'b0001;  // Enable only channel 0
    #(CLK_PERIOD * period * 3);  // Wait 3 periods
    
    // Check that disabled channels are inactive
    for (int i = 1; i < NUM_CHANNELS; i++) begin
      if (pwm[i] != 1'b0) begin
        $display("ERROR: Channel %0d should be inactive when disabled", i);
        error_count++;
      end
    end
    
    // Finish test
    #(CLK_PERIOD * 10);
    if (error_count == 0) begin
      $display("\nAll PWM tests PASSED!");
    end else begin
      $display("\nPWM tests FAILED with %0d errors", error_count);
    end
    
    $finish;
  end
  
  // Monitor for debug
  initial begin
    $monitor("Time: %t | Period: %0d | Ch0 Duty: %0d | Ch0 PWM: %b | Ch1 PWM: %b | Ch2 PWM: %b | Ch3 PWM: %b",
             $time, period, duty[0], pwm[0], pwm[1], pwm[2], pwm[3]);
  end

endmodule 