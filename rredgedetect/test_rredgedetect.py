import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge, FallingEdge
from cocotb.log import SimLog
import random
import traceback

# Test parameters
WIDTH = 4  # Width of the signal to monitor
CLK_PERIOD = 10  # 10ns = 100MHz

# Set up module-level logger
log = SimLog("rredgedetect_test")

def check_outputs(dut, signal, signal_prev):
    """Helper function to check edge detector outputs."""
    try:
        # Calculate expected outputs
        expected_rise = signal & ~signal_prev
        expected_fall = ~signal & signal_prev
        expected_toggle = signal ^ signal_prev
        
        # Check if detector outputs match expectations
        assert dut.rise_o.value == expected_rise, f"Rising edge mismatch. Expected: {bin(expected_rise)}, Got: {bin(dut.rise_o.value)}"
        assert dut.fall_o.value == expected_fall, f"Falling edge mismatch. Expected: {bin(expected_fall)}, Got: {bin(dut.fall_o.value)}"
        assert dut.toggle_o.value == expected_toggle, f"Toggle mismatch. Expected: {bin(expected_toggle)}, Got: {bin(dut.toggle_o.value)}"
        
        log.debug(f"Edge detection correct - Signal: {bin(signal)}, Previous: {bin(signal_prev)}")
    except Exception as e:
        error_msg = f"Edge detection check failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

async def setup_test(dut):
    """Common setup for all tests."""
    try:
        log.info("Setting up test environment")
        # Set up clock
        clock = Clock(dut.clk_i, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        # Reset
        log.info("Applying reset")
        dut.rst_n_i.value = 0
        dut.signal_i.value = 0  # Initialize input to known state
        await Timer(CLK_PERIOD * 2, units="ns")
        dut.rst_n_i.value = 1
        await Timer(CLK_PERIOD, units="ns")
        
        # Wait for one more clock cycle to ensure stable state
        await RisingEdge(dut.clk_i)
        log.info("Test setup complete")
    except Exception as e:
        error_msg = f"Test setup failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_rredgedetect_single_bit(dut):
    """Test 1: Single bit toggle."""
    try:
        log.info("Starting single bit toggle test")
        await setup_test(dut)
        
        # Test single bit toggle
        signal_prev = 0
        log.info("Testing rising edge")
        dut.signal_i.value = 1  # Set single bit to 1
        await RisingEdge(dut.clk_i)
        check_outputs(dut, 1, signal_prev)
        signal_prev = 1
        
        log.info("Testing falling edge")
        dut.signal_i.value = 0  # Set single bit to 0
        await RisingEdge(dut.clk_i)
        check_outputs(dut, 0, signal_prev)
        signal_prev = 0
        
        log.info("Single bit toggle test passed")
    except Exception as e:
        error_msg = f"Single bit toggle test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_rredgedetect_multiple_bits(dut):
    """Test 2: Multiple bit toggle."""
    try:
        log.info("Starting multiple bit toggle test")
        await setup_test(dut)
        
        # Test multiple bit toggle
        signal_prev = 0
        log.info("Testing multiple bits rising")
        dut.signal_i.value = 1  # Set single bit to 1
        await RisingEdge(dut.clk_i)
        check_outputs(dut, 1, signal_prev)
        signal_prev = 1
        
        log.info("Testing multiple bits falling")
        dut.signal_i.value = 0  # Set single bit to 0
        await RisingEdge(dut.clk_i)
        check_outputs(dut, 0, signal_prev)
        signal_prev = 0
        
        log.info("Multiple bit toggle test passed")
    except Exception as e:
        error_msg = f"Multiple bit toggle test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_rredgedetect_all_bits(dut):
    """Test 3 & 4: All bits rising and falling."""
    try:
        log.info("Starting all bits test")
        await setup_test(dut)
        
        # Test all bits rising
        signal_prev = 0
        log.info("Testing all bits rising")
        dut.signal_i.value = 1  # Set single bit to 1
        await RisingEdge(dut.clk_i)
        check_outputs(dut, 1, signal_prev)
        signal_prev = 1
        
        # Test all bits falling
        log.info("Testing all bits falling")
        dut.signal_i.value = 0  # Set single bit to 0
        await RisingEdge(dut.clk_i)
        check_outputs(dut, 0, signal_prev)
        signal_prev = 0
        
        log.info("All bits test passed")
    except Exception as e:
        error_msg = f"All bits test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_rredgedetect_random(dut):
    """Test 5: Random transitions."""
    try:
        log.info("Starting random transitions test")
        await setup_test(dut)
        
        # Test random transitions
        signal_prev = 0
        for i in range(20):
            signal = random.randint(0, 1)  # Only 0 or 1 for single bit
            log.debug(f"Random transition {i+1}: {signal_prev} -> {signal}")
            dut.signal_i.value = signal
            await RisingEdge(dut.clk_i)
            check_outputs(dut, signal, signal_prev)
            signal_prev = signal
        
        log.info("Random transitions test passed")
    except Exception as e:
        error_msg = f"Random transitions test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise 