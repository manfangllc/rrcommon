module dff #(
    parameter DATA_WIDTH = 1
) (
    input  logic                 clk,    // Clock input
    input  logic                 rst_n,  // Active-low reset
    input  logic [DATA_WIDTH-1:0] d_i,   // Data input
    output logic [DATA_WIDTH-1:0] q_o    // Data output
);

    // Sequential logic for D flip-flop
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            q_o <= '0;  // Reset to all zeros
        end else begin
            q_o <= d_i; // Sample input on clock edge
        end
    end

endmodule 