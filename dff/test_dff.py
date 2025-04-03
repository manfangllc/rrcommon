import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge, FallingEdge
from cocotb.log import SimLog
import random
import traceback

# Test parameters
CLK_PERIOD = 10      # Clock period in ns
INIT_DELAY = 50      # Initial delay for signal settling
RESET_DELAY = 50     # Reset hold time
SETUP_TIME = 2       # Setup time before clock edge
HOLD_TIME = 2        # Hold time after clock edge

# Module-level logger
log = SimLog("dff_test")

async def add_wave_marker(dut, name):
    """Add a marker to the waveform for debugging."""
    log.debug(f"Adding waveform marker: {name}")
    await Timer(1, units="ns")

async def initialize_dut(dut):
    """Initialize DUT inputs to known states."""
    dut.clk.value = 0
    dut.rst_n.value = 1
    dut.d_i.value = 0
    await Timer(1, units="ns")
    log.debug("DUT inputs initialized")

async def reset_dut(dut):
    """Apply reset sequence to DUT."""
    log.info("Applying reset")
    await add_wave_marker(dut, "Reset Start")
    dut.rst_n.value = 0
    await Timer(RESET_DELAY, units="ns")
    log.debug(f"During reset: outputs = {dut.q_o.value}")
    await add_wave_marker(dut, "Reset End")
    dut.rst_n.value = 1
    await Timer(CLK_PERIOD, units="ns")
    log.debug(f"After reset: outputs = {dut.q_o.value}")

async def set_input_with_timing(dut, value):
    """Set input with proper setup and hold timing."""
    await Timer(SETUP_TIME, units="ns")
    dut.d_i.value = value
    await RisingEdge(dut.clk)
    await Timer(HOLD_TIME, units="ns")
    log.debug(f"Input set to {value}")

@cocotb.test()
async def test_reset_functionality(dut):
    """Test 1: Reset functionality"""
    try:
        log.info("Starting reset functionality test")
        
        # Initialize DUT
        await initialize_dut(dut)
        
        # Setup clock
        clock = Clock(dut.clk, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        await Timer(INIT_DELAY, units="ns")
        
        # Test reset assertion
        await reset_dut(dut)
        assert dut.q_o.value == 0, f"Reset failed: output = {dut.q_o.value}, expected 0"
        
        # Test reset deassertion and data capture
        test_value = 1
        await set_input_with_timing(dut, test_value)
        assert dut.q_o.value == test_value, f"Data capture failed: got {dut.q_o.value}, expected {test_value}"
        
        log.info("Reset functionality test passed")
    except Exception as e:
        error_msg = f"Reset test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_data_capture(dut):
    """Test 2: Data capture with various patterns"""
    try:
        log.info("Starting data capture test")
        
        # Initialize DUT
        await initialize_dut(dut)
        
        # Setup clock
        clock = Clock(dut.clk, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        await Timer(INIT_DELAY, units="ns")
        
        # Reset DUT
        await reset_dut(dut)
        
        # Test various input patterns for 1-bit
        test_patterns = [0, 1, 0, 1, 1, 0]
        for pattern in test_patterns:
            await set_input_with_timing(dut, pattern)
            assert dut.q_o.value == pattern, f"Data capture failed: got {dut.q_o.value}, expected {pattern}"
            log.debug(f"Successfully captured pattern: {pattern}")
        
        log.info("Data capture test passed")
    except Exception as e:
        error_msg = f"Data capture test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_clock_edge_sensitivity(dut):
    """Test 3: Clock edge sensitivity"""
    try:
        log.info("Starting clock edge sensitivity test")
        
        # Initialize DUT
        await initialize_dut(dut)
        
        # Setup clock
        clock = Clock(dut.clk, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        await Timer(INIT_DELAY, units="ns")
        
        # Reset DUT
        await reset_dut(dut)
        
        # Test input changes between clock edges
        initial_value = 0
        await set_input_with_timing(dut, initial_value)
        assert dut.q_o.value == initial_value, f"Initial value capture failed"
        
        # Change input between clock edges
        dut.d_i.value = 1
        await Timer(CLK_PERIOD/2, units="ns")  # Wait half clock period
        assert dut.q_o.value == initial_value, f"Output changed between clock edges"
        
        # Verify change on next clock edge
        await RisingEdge(dut.clk)
        await Timer(HOLD_TIME, units="ns")
        assert dut.q_o.value == 1, f"Output didn't change on clock edge"
        
        log.info("Clock edge sensitivity test passed")
    except Exception as e:
        error_msg = f"Clock edge test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_reset_timing(dut):
    """Test 4: Reset timing"""
    try:
        log.info("Starting reset timing test")
        
        # Initialize DUT
        await initialize_dut(dut)
        
        # Setup clock
        clock = Clock(dut.clk, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        await Timer(INIT_DELAY, units="ns")
        
        # Test reset during normal operation
        await set_input_with_timing(dut, 1)
        assert dut.q_o.value == 1, "Initial data capture failed"
        
        # Assert reset during operation
        await Timer(CLK_PERIOD/2, units="ns")
        dut.rst_n.value = 0
        dut.d_i.value = 0  # Set input to 0 during reset
        await Timer(RESET_DELAY, units="ns")
        assert dut.q_o.value == 0, "Reset during operation failed"
        
        # Test reset deassertion timing
        dut.rst_n.value = 1
        await Timer(CLK_PERIOD, units="ns")
        assert dut.q_o.value == 0, "Reset deassertion timing failed"
        
        log.info("Reset timing test passed")
    except Exception as e:
        error_msg = f"Reset timing test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_data_width_parameter(dut):
    """Test 5: 1-bit operation test"""
    try:
        log.info("Starting 1-bit operation test")
        
        # Initialize DUT
        await initialize_dut(dut)
        
        # Setup clock
        clock = Clock(dut.clk, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        await Timer(INIT_DELAY, units="ns")
        
        # Reset DUT
        await reset_dut(dut)
        
        # Verify we're working with 1-bit
        data_width = len(dut.d_i)
        assert data_width == 1, f"Expected 1-bit DFF, got {data_width}-bit"
        log.info("Confirmed 1-bit operation")
        
        # Test both possible values for 1-bit
        test_values = [0, 1]
        
        for value in test_values:
            await add_wave_marker(dut, f"Testing value {value}")
            await set_input_with_timing(dut, value)
            await Timer(CLK_PERIOD/2, units="ns")  # Wait for output to stabilize
            assert dut.q_o.value == value, f"1-bit test failed: got {dut.q_o.value}, expected {value}"
            log.debug(f"Successfully captured value: {value}")
            
            # Test reset during operation
            if value == 1:  # Only test reset for '1' since '0' is reset value
                dut.rst_n.value = 0
                await Timer(RESET_DELAY, units="ns")
                assert dut.q_o.value == 0, "Reset failed during operation"
                dut.rst_n.value = 1
                await Timer(CLK_PERIOD, units="ns")
        
        log.info("1-bit operation test passed")
    except Exception as e:
        error_msg = f"1-bit test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise