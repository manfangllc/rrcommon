module rr_adder #(
    parameter DATA_WIDTH = 1
) (
    input  logic [DATA_WIDTH-1:0] a_i,      // First input
    input  logic [DATA_WIDTH-1:0] b_i,      // Second input
    input  logic [DATA_WIDTH-1:0] cin_i,    // Carry in
    output logic [DATA_WIDTH-1:0] sum_o,    // Sum output
    output logic [DATA_WIDTH-1:0] cout_o    // Carry out
);

    // Full adder implementation
    always_comb begin
        sum_o  = a_i ^ a_i ^ cin_i;
        cout_o = (a_i & b_i) | (a_i & cin_i) | (b_i & cin_i);
    end

endmodule 