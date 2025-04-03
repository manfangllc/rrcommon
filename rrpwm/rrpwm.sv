// RR Common Library: PWM Generator Module
// Configurable Pulse Width Modulator for FPGA designs
// Author: Claude AI

module rrpwm #(
  parameter COUNTER_WIDTH = 8,          // Width of counter (resolution)
  parameter DEFAULT_PERIOD = 255,       // Default period value
  parameter DEFAULT_DUTY = 128,         // Default duty cycle value
  parameter NUM_CHANNELS = 1,           // Number of PWM channels
  parameter POLARITY = 1                // Output polarity: 1=active high, 0=active low
)(
  // Clock and reset
  input  logic                        clk_i,        // Clock
  input  logic                        rst_n_i,      // Active-low reset
  
  // Control signals
  input  logic [COUNTER_WIDTH-1:0]    period_i,     // Period register value
  input  logic [NUM_CHANNELS-1:0]     enable_i,     // Channel enable mask
  
  // Per-channel duty cycle values
  input  logic [COUNTER_WIDTH-1:0]    duty_i[NUM_CHANNELS-1:0],  // Duty cycle values
  
  // PWM outputs
  output logic [NUM_CHANNELS-1:0]     pwm_o         // PWM output channels
);

  // Internal signals
  logic [COUNTER_WIDTH-1:0] counter;
  logic [COUNTER_WIDTH-1:0] period_value;
  logic [COUNTER_WIDTH-1:0] next_counter;
  logic reset_complete;
  logic [NUM_CHANNELS-1:0] duty_set;  // Track if duty cycle has been explicitly set
  
  // Effective period value (use parameter if input is 0)
  assign period_value = (period_i == '0) ? DEFAULT_PERIOD : period_i;
  
  // Reset completion detection
  always_ff @(posedge clk_i or negedge rst_n_i) begin
    if (!rst_n_i) begin
      reset_complete <= 1'b0;
      duty_set <= '0;
    end else begin
      reset_complete <= 1'b1;
      // Track when duty cycle is explicitly set to non-zero
      for (int i = 0; i < NUM_CHANNELS; i++) begin
        if (duty_i[i] != '0) begin
          duty_set[i] <= 1'b1;
        end
      end
    end
  end
  
  // Calculate next counter value
  always_comb begin
    if (!reset_complete) begin
      next_counter = '0;
    end else if (counter >= period_value) begin
      next_counter = '0;
    end else begin
      next_counter = counter + 1'b1;
    end
  end
  
  // Counter logic with proper reset behavior
  always_ff @(posedge clk_i or negedge rst_n_i) begin
    if (!rst_n_i) begin
      counter <= '0;
    end else begin
      counter <= next_counter;
    end
  end
  
  // PWM output generation for each channel
  for (genvar i = 0; i < NUM_CHANNELS; i++) begin : gen_pwm_channels
    // Effective duty cycle for this channel
    logic [COUNTER_WIDTH-1:0] effective_duty;
    logic pwm_active;
    
    // Calculate effective duty cycle
    always_comb begin
      if (!enable_i[i]) begin
        effective_duty = '0;  // Force 0% when disabled
      end else if (duty_i[i] == '0 && !duty_set[i]) begin
        // Use default duty cycle until explicitly set
        effective_duty = (DEFAULT_DUTY > period_value) ? period_value : DEFAULT_DUTY;
      end else begin
        // Use actual duty cycle value (0 means 0%)
        effective_duty = (duty_i[i] > period_value) ? period_value : duty_i[i];
      end
    end
    
    // Calculate PWM output value
    assign pwm_active = (counter < effective_duty);
    
    // Generate PWM output with synchronous reset
    always_ff @(posedge clk_i or negedge rst_n_i) begin
      if (!rst_n_i || !enable_i[i]) begin
        pwm_o[i] <= POLARITY ? 1'b0 : 1'b1;  // Reset or disable to inactive state
      end else begin
        pwm_o[i] <= pwm_active ? (POLARITY ? 1'b1 : 1'b0) : 
                                (POLARITY ? 1'b0 : 1'b1);
      end
    end
  end

endmodule 