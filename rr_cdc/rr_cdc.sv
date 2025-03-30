// RR Common Library: Clock Domain Crossing Module
// Safe synchronization between different clock domains
// Author: Claude AI

module rr_cdc #(
  parameter WIDTH = 1,          // Width of data bus
  parameter SYNC_STAGES = 2,    // Number of synchronizer stages (2 or 3 recommended)
  parameter MODE = "PULSE",     // "PULSE", "TOGGLE", or "HANDSHAKE"
  parameter RESET_VALUE = '0    // Reset value for synchronizer stages
)(
  // Source domain signals
  input  logic                clk_src_i,    // Source clock
  input  logic                rst_src_n_i,  // Source reset (active low)
  input  logic [WIDTH-1:0]    data_src_i,   // Source data input
  input  logic                valid_src_i,  // Source valid signal
  output logic                ready_src_o,  // Source ready signal (for handshaking)
  
  // Destination domain signals
  input  logic                clk_dst_i,    // Destination clock
  input  logic                rst_dst_n_i,  // Destination reset (active low)
  output logic [WIDTH-1:0]    data_dst_o,   // Synchronized data output
  output logic                valid_dst_o,  // Destination valid signal
  input  logic                ready_dst_i   // Destination ready signal (for handshaking)
);

  // --------------------------------------------------
  // Mode-specific internal signals
  // --------------------------------------------------
  
  // Signals for pulse synchronizer
  logic pulse_src;             // Source pulse to synchronize
  logic pulse_synced;          // Synchronized pulse
  
  // Signals for toggle synchronizer
  logic toggle_src;            // Source toggle signal
  logic toggle_synced;         // Synchronized toggle
  logic toggle_synced_prev;    // Previous value for edge detection
  
  // Signals for handshaking
  logic req_src;               // Source request
  logic req_synced;            // Synchronized request
  logic ack_dst;               // Destination acknowledge
  logic ack_synced;            // Synchronized acknowledge
  logic req_src_prev;          // Previous request for edge detection
  logic ack_synced_prev;       // Previous acknowledge for edge detection

  // --------------------------------------------------
  // Mode-specific implementations
  // --------------------------------------------------
  
  generate
    // PULSE mode: Synchronize a single-cycle pulse across domains
    if (MODE == "PULSE") begin : gen_pulse
      // Source domain logic
      always_ff @(posedge clk_src_i or negedge rst_src_n_i) begin
        if (!rst_src_n_i) begin
          pulse_src <= 1'b0;
          ready_src_o <= 1'b1;
        end else begin
          // Generate pulse when valid_src_i asserted
          pulse_src <= valid_src_i & ready_src_o;
          // Always ready in pulse mode (assumes pulses aren't too frequent)
          ready_src_o <= 1'b1;
        end
      end
      
      // Capture data on pulse
      always_ff @(posedge clk_src_i or negedge rst_src_n_i) begin
        if (!rst_src_n_i) begin
          data_dst_o <= RESET_VALUE;
        end else if (valid_src_i & ready_src_o) begin
          data_dst_o <= data_src_i;
        end
      end
      
      // Synchronize pulse to destination domain
      sync_chain #(
        .WIDTH(1),
        .STAGES(SYNC_STAGES),
        .RESET_VALUE(1'b0)
      ) pulse_synchronizer (
        .clk_i(clk_dst_i),
        .rst_n_i(rst_dst_n_i),
        .data_i(pulse_src),
        .data_o(pulse_synced)
      );
      
      // Edge detection in destination domain
      logic pulse_synced_prev;
      always_ff @(posedge clk_dst_i or negedge rst_dst_n_i) begin
        if (!rst_dst_n_i) begin
          pulse_synced_prev <= 1'b0;
          valid_dst_o <= 1'b0;
        end else begin
          pulse_synced_prev <= pulse_synced;
          // Rising edge detection
          valid_dst_o <= pulse_synced & ~pulse_synced_prev;
        end
      end
    end
    
    // TOGGLE mode: Toggle a bit to signal new data
    else if (MODE == "TOGGLE") begin : gen_toggle
      // Source domain toggle on valid data
      always_ff @(posedge clk_src_i or negedge rst_src_n_i) begin
        if (!rst_src_n_i) begin
          toggle_src <= 1'b0;
          ready_src_o <= 1'b1;
        end else if (valid_src_i & ready_src_o) begin
          toggle_src <= ~toggle_src;
          ready_src_o <= 1'b1;  // Always ready in toggle mode
        end
      end
      
      // Capture data on toggle
      always_ff @(posedge clk_src_i or negedge rst_src_n_i) begin
        if (!rst_src_n_i) begin
          data_dst_o <= RESET_VALUE;
        end else if (valid_src_i & ready_src_o) begin
          data_dst_o <= data_src_i;
        end
      end
      
      // Synchronize toggle to destination domain
      sync_chain #(
        .WIDTH(1),
        .STAGES(SYNC_STAGES),
        .RESET_VALUE(1'b0)
      ) toggle_synchronizer (
        .clk_i(clk_dst_i),
        .rst_n_i(rst_dst_n_i),
        .data_i(toggle_src),
        .data_o(toggle_synced)
      );
      
      // Edge detection in destination domain
      always_ff @(posedge clk_dst_i or negedge rst_dst_n_i) begin
        if (!rst_dst_n_i) begin
          toggle_synced_prev <= 1'b0;
          valid_dst_o <= 1'b0;
        end else begin
          toggle_synced_prev <= toggle_synced;
          // Toggle detection (any change)
          valid_dst_o <= toggle_synced != toggle_synced_prev;
        end
      end
    end
    
    // HANDSHAKE mode: Full req/ack handshaking
    else if (MODE == "HANDSHAKE") begin : gen_handshake
      // Source domain request generation and acknowledge detection
      always_ff @(posedge clk_src_i or negedge rst_src_n_i) begin
        if (!rst_src_n_i) begin
          req_src <= 1'b0;
          req_src_prev <= 1'b0;
          ack_synced_prev <= 1'b0;
          ready_src_o <= 1'b1;
        end else begin
          req_src_prev <= req_src;
          ack_synced_prev <= ack_synced;
          
          // Set request when valid and ready
          if (valid_src_i & ready_src_o & !req_src) begin
            req_src <= 1'b1;
            ready_src_o <= 1'b0;  // Not ready while handshaking
          end 
          // Clear request when acknowledge edge detected
          else if (req_src & (ack_synced & ~ack_synced_prev)) begin
            req_src <= 1'b0;
            ready_src_o <= 1'b1;  // Ready for new data after handshake
          end
        end
      end
      
      // Capture data on handshake start
      always_ff @(posedge clk_src_i or negedge rst_src_n_i) begin
        if (!rst_src_n_i) begin
          data_dst_o <= RESET_VALUE;
        end else if (valid_src_i & ready_src_o) begin
          data_dst_o <= data_src_i;
        end
      end
      
      // Synchronize request to destination domain
      sync_chain #(
        .WIDTH(1),
        .STAGES(SYNC_STAGES),
        .RESET_VALUE(1'b0)
      ) req_synchronizer (
        .clk_i(clk_dst_i),
        .rst_n_i(rst_dst_n_i),
        .data_i(req_src),
        .data_o(req_synced)
      );
      
      // Destination domain acknowledge generation
      always_ff @(posedge clk_dst_i or negedge rst_dst_n_i) begin
        if (!rst_dst_n_i) begin
          ack_dst <= 1'b0;
          valid_dst_o <= 1'b0;
        end else begin
          // New request detected
          if (req_synced & !ack_dst) begin
            valid_dst_o <= 1'b1;
            
            // Ready consumer accepts data, generate acknowledge
            if (ready_dst_i) begin
              ack_dst <= 1'b1;
              valid_dst_o <= 1'b0;
            end
          end
          // Request cleared, reset acknowledge
          else if (!req_synced & ack_dst) begin
            ack_dst <= 1'b0;
            valid_dst_o <= 1'b0;
          end
        end
      end
      
      // Synchronize acknowledge back to source domain
      sync_chain #(
        .WIDTH(1),
        .STAGES(SYNC_STAGES),
        .RESET_VALUE(1'b0)
      ) ack_synchronizer (
        .clk_i(clk_src_i),
        .rst_n_i(rst_src_n_i),
        .data_i(ack_dst),
        .data_o(ack_synced)
      );
    end
  endgenerate
  
  // --------------------------------------------------
  // Multi-stage synchronizer submodule
  // --------------------------------------------------
  
  // Internal multi-stage synchronizer
  module sync_chain #(
    parameter WIDTH = 1,           // Data width
    parameter STAGES = 2,          // Number of synchronizer stages
    parameter RESET_VALUE = '0     // Value to set on reset
  )(
    input  logic              clk_i,    // Destination clock
    input  logic              rst_n_i,  // Destination reset (active low)
    input  logic [WIDTH-1:0]  data_i,   // Asynchronous input data
    output logic [WIDTH-1:0]  data_o    // Synchronized output data
  );
    // Synchronizer flip-flop chain
    logic [WIDTH-1:0] sync_stages [STAGES-1:0];
    
    always_ff @(posedge clk_i or negedge rst_n_i) begin
      if (!rst_n_i) begin
        // Reset all stages to defined value
        for (int i = 0; i < STAGES; i++) begin
          sync_stages[i] <= RESET_VALUE;
        end
      end else begin
        // First stage samples the async input
        sync_stages[0] <= data_i;
        
        // Subsequent stages form the synchronization chain
        for (int i = 1; i < STAGES; i++) begin
          sync_stages[i] <= sync_stages[i-1];
        end
      end
    end
    
    // Output is the last stage
    assign data_o = sync_stages[STAGES-1];
  endmodule
  
endmodule 