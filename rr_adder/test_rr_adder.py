import cocotb
from cocotb.triggers import Timer, RisingEdge
import traceback

def log_test_progress(dut, message):
    """Helper function to log test progress with consistent formatting."""
    dut._log.info(f"Test Progress: {message}")

def log_data_transfer(dut, a, b, cin, sum_val, cout_val):
    """Helper function to log data transfer details."""
    dut._log.info(f"Data Transfer: a={a}, b={b}, cin={cin}, sum={sum_val}, cout={cout_val}")

def format_error_message(test_num, a, b, cin, expected_sum, actual_sum, is_sum=True):
    """Helper function to format error messages consistently."""
    if is_sum:
        return (
            f"Sum mismatch in test case {test_num}:\n"
            f"Inputs: a={a}, b={b}, cin={cin}\n"
            f"Expected sum: {expected_sum}\n"
            f"Actual sum: {actual_sum}"
        )
    else:
        return (
            f"Carry mismatch in test case {test_num}:\n"
            f"Inputs: a={a}, b={b}, cin={cin}\n"
            f"Expected carry: {expected_sum}\n"
            f"Actual carry: {actual_sum}"
        )

@cocotb.test()
async def rr_adder_test(dut):
    """Test the rr_adder module with all possible input combinations."""
    try:
        # Initialize signals
        dut.a_i.value = 0
        dut.b_i.value = 0
        dut.cin_i.value = 0
        await Timer(50, units="ns")  # Longer initial wait for better visibility
        
        log_test_progress(dut, "Starting single-bit adder test suite")
        
        # Test all possible combinations for single-bit adder
        test_cases = [
            # a_i, b_i, cin_i, expected_sum, expected_cout
            (0, 0, 0, 0, 0),  # Test case 1: 0 + 0 + 0 = 0
            (0, 0, 1, 1, 0),  # Test case 2: 0 + 0 + 1 = 1
            (0, 1, 0, 1, 0),  # Test case 3: 0 + 1 + 0 = 1
            (0, 1, 1, 0, 1),  # Test case 4: 0 + 1 + 1 = 2 (carry)
            (1, 0, 0, 1, 0),  # Test case 5: 1 + 0 + 0 = 1
            (1, 0, 1, 0, 1),  # Test case 6: 1 + 0 + 1 = 2 (carry)
            (1, 1, 0, 0, 1),  # Test case 7: 1 + 1 + 0 = 2 (carry)
            (1, 1, 1, 1, 1)   # Test case 8: 1 + 1 + 1 = 3 (carry)
        ]

        # Test each case
        for test_num, (a, b, cin, expected_sum, expected_cout) in enumerate(test_cases, 1):
            try:
                log_test_progress(dut, f"Starting test case {test_num}")
                
                # Drive inputs
                dut.a_i.value = a
                dut.b_i.value = b
                dut.cin_i.value = cin
                
                # Wait for a longer delay to allow combinational logic to settle
                await Timer(50, units="ns")
                
                # Log the data transfer
                log_data_transfer(dut, a, b, cin, dut.sum_o.value, dut.cout_o.value)
                
                # Check outputs with detailed error messages
                if dut.sum_o.value != expected_sum:
                    error_msg = format_error_message(test_num, a, b, cin, expected_sum, dut.sum_o.value, True)
                    dut._log.error(error_msg)
                    raise AssertionError(error_msg)
                
                if dut.cout_o.value != expected_cout:
                    error_msg = format_error_message(test_num, a, b, cin, expected_cout, dut.cout_o.value, False)
                    dut._log.error(error_msg)
                    raise AssertionError(error_msg)
                
                log_test_progress(dut, f"Test case {test_num} passed successfully")
                
                # Add a small delay between test cases for better waveform visibility
                await Timer(50, units="ns")
                
            except Exception as e:
                dut._log.error(f"Test case {test_num} failed with error: {str(e)}")
                dut._log.error(f"Stack trace:\n{traceback.format_exc()}")
                raise
        
        log_test_progress(dut, "All single-bit adder test cases completed successfully")
        
    except Exception as e:
        dut._log.error(f"Test suite failed with error: {str(e)}")
        dut._log.error(f"Stack trace:\n{traceback.format_exc()}")
        raise

@cocotb.test(skip=True)  # Skip this test when DATA_WIDTH=1
async def rr_adder_multi_bit_test(dut):
    """Test the rr_adder module with multi-bit values. Only runs when DATA_WIDTH > 1."""
    try:
        # Skip test if DATA_WIDTH is 1
        if len(dut.a_i) == 1:
            dut._log.info("Skipping multi-bit test as DATA_WIDTH=1")
            return
        
        log_test_progress(dut, "Starting multi-bit adder test suite")
        
        # Test multi-bit addition
        test_cases = [
            # a_i, b_i, cin_i, expected_sum, expected_cout
            (0b0011, 0b0011, 0, 0b0110, 0),  # 3 + 3 = 6
            (0b1111, 0b0001, 0, 0b0000, 1),  # 15 + 1 = 16 (overflow)
            (0b1010, 0b0101, 0, 0b1111, 0),  # 10 + 5 = 15
            (0b1111, 0b1111, 1, 0b1111, 1),  # 15 + 15 + 1 = 31 (overflow)
        ]

        # Test each case
        for test_num, (a, b, cin, expected_sum, expected_cout) in enumerate(test_cases, 1):
            try:
                log_test_progress(dut, f"Starting multi-bit test case {test_num}")
                
                # Drive inputs
                dut.a_i.value = a
                dut.b_i.value = b
                dut.cin_i.value = cin
                
                # Wait for a small delay to allow combinational logic to settle
                await Timer(1, units="ns")
                
                # Log the data transfer
                log_data_transfer(dut, bin(a), bin(b), cin, bin(dut.sum_o.value), dut.cout_o.value)
                
                # Check outputs with detailed error messages
                if dut.sum_o.value != expected_sum:
                    error_msg = (
                        f"Sum mismatch in multi-bit test case {test_num}:\n"
                        f"Inputs: a={bin(a)}, b={bin(b)}, cin={cin}\n"
                        f"Expected sum: {bin(expected_sum)}\n"
                        f"Actual sum: {bin(dut.sum_o.value)}"
                    )
                    dut._log.error(error_msg)
                    raise AssertionError(error_msg)
                
                if dut.cout_o.value != expected_cout:
                    error_msg = (
                        f"Carry mismatch in multi-bit test case {test_num}:\n"
                        f"Inputs: a={bin(a)}, b={bin(b)}, cin={cin}\n"
                        f"Expected carry: {expected_cout}\n"
                        f"Actual carry: {dut.cout_o.value}"
                    )
                    dut._log.error(error_msg)
                    raise AssertionError(error_msg)
                
                log_test_progress(dut, f"Multi-bit test case {test_num} passed successfully")
                
            except Exception as e:
                dut._log.error(f"Multi-bit test case {test_num} failed with error: {str(e)}")
                dut._log.error(f"Stack trace:\n{traceback.format_exc()}")
                raise
        
        log_test_progress(dut, "All multi-bit adder test cases completed successfully")
        
    except Exception as e:
        dut._log.error(f"Multi-bit test suite failed with error: {str(e)}")
        dut._log.error(f"Stack trace:\n{traceback.format_exc()}")
        raise 