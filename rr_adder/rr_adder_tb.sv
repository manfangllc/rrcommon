module rr_adder_tb;

    // Test parameters
    localparam DATA_WIDTH = 1;
    
    // Test signals
    logic [DATA_WIDTH-1:0] a_i, b_i, cin_i;
    logic [DATA_WIDTH-1:0] sum_o, cout_o;
    
    // Instantiate the full adder
    rr_adder #(
        .DATA_WIDTH(DATA_WIDTH)
    ) dut (
        .a_i(a_i),
        .b_i(b_i),
        .cin_i(cin_i),
        .sum_o(sum_o),
        .cout_o(cout_o)
    );
    
    // Test stimulus
    initial begin
        // Test case 1: 0 + 0 + 0
        a_i = 1'b0; b_i = 1'b0; cin_i = 1'b0;
        #10;
        assert(sum_o === 1'b0 && cout_o === 1'b0) 
            $display("Test 1 PASSED: 0 + 0 + 0 = 0, cout = 0");
        else $error("Test 1 FAILED: 0 + 0 + 0");
        
        // Test case 2: 0 + 0 + 1
        a_i = 1'b0; b_i = 1'b0; cin_i = 1'b1;
        #10;
        assert(sum_o === 1'b1 && cout_o === 1'b0)
            $display("Test 2 PASSED: 0 + 0 + 1 = 1, cout = 0");
        else $error("Test 2 FAILED: 0 + 0 + 1");
        
        // Test case 3: 0 + 1 + 0
        a_i = 1'b0; b_i = 1'b1; cin_i = 1'b0;
        #10;
        assert(sum_o === 1'b1 && cout_o === 1'b0)
            $display("Test 3 PASSED: 0 + 1 + 0 = 1, cout = 0");
        else $error("Test 3 FAILED: 0 + 1 + 0");
        
        // Test case 4: 0 + 1 + 1
        a_i = 1'b0; b_i = 1'b1; cin_i = 1'b1;
        #10;
        assert(sum_o === 1'b0 && cout_o === 1'b1)
            $display("Test 4 PASSED: 0 + 1 + 1 = 0, cout = 1");
        else $error("Test 4 FAILED: 0 + 1 + 1");
        
        // Test case 5: 1 + 0 + 0
        a_i = 1'b1; b_i = 1'b0; cin_i = 1'b0;
        #10;
        assert(sum_o === 1'b1 && cout_o === 1'b0)
            $display("Test 5 PASSED: 1 + 0 + 0 = 1, cout = 0");
        else $error("Test 5 FAILED: 1 + 0 + 0");
        
        // Test case 6: 1 + 0 + 1
        a_i = 1'b1; b_i = 1'b0; cin_i = 1'b1;
        #10;
        assert(sum_o === 1'b0 && cout_o === 1'b1)
            $display("Test 6 PASSED: 1 + 0 + 1 = 0, cout = 1");
        else $error("Test 6 FAILED: 1 + 0 + 1");
        
        // Test case 7: 1 + 1 + 0
        a_i = 1'b1; b_i = 1'b1; cin_i = 1'b0;
        #10;
        assert(sum_o === 1'b0 && cout_o === 1'b1)
            $display("Test 7 PASSED: 1 + 1 + 0 = 0, cout = 1");
        else $error("Test 7 FAILED: 1 + 1 + 0");
        
        // Test case 8: 1 + 1 + 1
        a_i = 1'b1; b_i = 1'b1; cin_i = 1'b1;
        #10;
        assert(sum_o === 1'b1 && cout_o === 1'b1)
            $display("Test 8 PASSED: 1 + 1 + 1 = 1, cout = 1");
        else $error("Test 8 FAILED: 1 + 1 + 1");
        
        $display("All tests completed!");
        $finish;
    end

endmodule 