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

  // Internal counter for PWM generation
  logic [COUNTER_WIDTH-1:0] counter;
  
  // Effective period value (use parameter if input is 0)
  logic [COUNTER_WIDTH-1:0] period_value;
  assign period_value = (period_i == '0) ? DEFAULT_PERIOD : period_i;
  
  // Counter logic
  always_ff @(posedge clk_i or negedge rst_n_i) begin
    if (!rst_n_i) begin
      counter <= '0;
    end else begin
      if (counter >= period_value) begin
        // Reset counter at end of period
        counter <= '0;
      end else begin
        // Increment counter
        counter <= counter + 1'b1;
      end
    end
  end
  
  // PWM output generation for each channel
  for (genvar i = 0; i < NUM_CHANNELS; i++) begin : gen_pwm_channels
    // Effective duty cycle for this channel (use parameter if input is 0)
    logic [COUNTER_WIDTH-1:0] effective_duty;
    
    always_comb begin
      // Use default duty if input is 0 or if duty > period
      if (duty_i[i] == '0 || duty_i[i] > period_value) begin
        effective_duty = (DEFAULT_DUTY > period_value) ? period_value : DEFAULT_DUTY;
      end else begin
        effective_duty = duty_i[i];
      end
    end
    
    // Generate PWM output by comparing counter to duty cycle
    always_ff @(posedge clk_i or negedge rst_n_i) begin
      if (!rst_n_i) begin
        pwm_o[i] <= POLARITY ? 1'b0 : 1'b1;  // Respect polarity on reset
      end else if (!enable_i[i]) begin
        pwm_o[i] <= POLARITY ? 1'b0 : 1'b1;  // Inactive state when disabled
      end else begin
        // Active when counter < duty cycle (with polarity control)
        pwm_o[i] <= (counter < effective_duty) ? 
                    (POLARITY ? 1'b1 : 1'b0) : (POLARITY ? 1'b0 : 1'b1);
      end
    end
  end

endmodule 