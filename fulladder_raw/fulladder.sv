module fulladder (
    input  logic a,    // First input
    input  logic b,    // Second input
    input  logic cin,  // Carry in
    output logic sum,  // Sum output
    output logic cout  // Carry out
);

    // Full adder logic
    assign sum = a ^ b ^ cin;
    assign cout = (a & b) | (cin & (a ^ b));

    // Dump waves
    initial begin
        $dumpfile("fulladder.vcd");
        $dumpvars(0, fulladder);
    end

endmodule 