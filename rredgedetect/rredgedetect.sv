// RR Common Library: Edge Detector Module
// Detects rising, falling, and both edges on an input signal
// Author: Claude AI

module rredgedetect #(
  parameter WIDTH = 1  // Width of the signal to monitor
)(
  // Clock and reset
  input  logic              clk_i,     // Clock
  input  logic              rst_n_i,   // Active-low reset
  
  // Input signal
  input  logic [WIDTH-1:0]  signal_i,  // Input signal to monitor
  
  // Edge detection outputs
  output logic [WIDTH-1:0]  rise_o,    // Rising edge detected
  output logic [WIDTH-1:0]  fall_o,    // Falling edge detected
  output logic [WIDTH-1:0]  toggle_o   // Any edge detected (toggle)
);

  // Signal register for edge detection
  logic [WIDTH-1:0] signal_reg;

  // Register the input signal
  always_ff @(posedge clk_i or negedge rst_n_i) begin
    if (!rst_n_i) begin
      signal_reg <= '0;
    end else begin
      signal_reg <= signal_i;
    end
  end

  // Detect edges by comparing current and previous values
  always_comb begin
    // Rising edge: current is 1, previous was 0
    rise_o   = signal_i & ~signal_reg;
    
    // Falling edge: current is 0, previous was 1
    fall_o   = ~signal_i & signal_reg;
    
    // Toggle: Either edge (XOR of current and previous)
    toggle_o = signal_i ^ signal_reg;
  end

endmodule 