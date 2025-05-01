import cocotb
from cocotb.triggers import Timer
from cocotb.binary import BinaryValue
import itertools

@cocotb.test()
async def test_fulladder(dut):
    """Test all possible combinations for the full adder"""
    
    # Create all possible input combinations
    for a, b, cin in itertools.product([0, 1], repeat=3):
        # Apply inputs
        dut.a.value = a
        dut.b.value = b
        dut.cin.value = cin
        
        # Wait for propagation
        await Timer(1, units='ns')
        
        # Calculate expected outputs
        expected_sum = a ^ b ^ cin
        expected_cout = (a & b) | (cin & (a ^ b))
        
        # Check outputs
        assert dut.sum.value == expected_sum, f"Sum mismatch for a={a}, b={b}, cin={cin}. Got {dut.sum.value}, expected {expected_sum}"
        assert dut.cout.value == expected_cout, f"Cout mismatch for a={a}, b={b}, cin={cin}. Got {dut.cout.value}, expected {expected_cout}"
        
        # Log results
        dut._log.info(f"Test passed for a={a}, b={b}, cin={cin}, sum={dut.sum.value}, cout={dut.cout.value}") 