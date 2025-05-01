import cocotb
from cocotb.triggers import Timer
from cocotb.binary import BinaryValue
from cocotb.clock import Clock

@cocotb.test()
async def test_fulladder(dut):
    """Test all possible input combinations for the full adder"""
    
    # Create a list to store test results
    test_results = []
    
    # Test all possible input combinations
    for a in range(2):
        for b in range(2):
            for cin in range(2):
                # Set the input values
                dut.a.value = a
                dut.b.value = b
                dut.cin.value = cin
                
                # Wait for combinational logic to settle
                await Timer(2, units='ns')
                
                # Calculate expected results
                expected_sum = (a ^ b ^ cin)
                expected_cout = ((a & b) | (cin & (a ^ b)))
                
                # Get actual results
                actual_sum = dut.sum.value
                actual_cout = dut.cout.value
                
                # Store results
                test_results.append({
                    'inputs': f'a={a} b={b} cin={cin}',
                    'expected': f'sum={expected_sum} cout={expected_cout}',
                    'actual': f'sum={actual_sum} cout={actual_cout}'
                })
                
                # Assert the results
                assert actual_sum == expected_sum, f"Sum mismatch for a={a}, b={b}, cin={cin}"
                assert actual_cout == expected_cout, f"Cout mismatch for a={a}, b={b}, cin={cin}"
                
                # Add some delay between tests for better waveform visibility
                await Timer(2, units='ns')
    
    # Print test results
    print("\nFull Adder Test Results:")
    print("-" * 60)
    for result in test_results:
        print(f"Inputs: {result['inputs']}")
        print(f"Expected: {result['expected']}")
        print(f"Actual: {result['actual']}")
        print("-" * 60) 