import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge, FallingEdge
from cocotb.log import SimLog
import random
import traceback

# Test parameters
CLK_PERIOD = 10  # 10ns = 100MHz
INIT_DELAY = 50  # Initial delay to allow signals to settle
RESET_DELAY = 50  # Reset hold time

# Module parameters (matching RTL)
COUNTER_WIDTH = 8
DEFAULT_PERIOD = 255
DEFAULT_DUTY = 128
NUM_CHANNELS = 1

# Setup module-level logger
log = SimLog("rrpwm_test")

async def add_wave_marker(dut, name):
    """Add a marker to the waveform for debugging."""
    log.debug(f"Adding waveform marker: {name}")
    await Timer(1, units="ns")

async def initialize_dut(dut):
    """Initialize DUT inputs."""
    dut.period_i.value = 0  # Use default period
    dut.enable_i.value = 0  # Start disabled
    dut.duty_i[0].value = 0  # Use default duty cycle
    await Timer(1, units="ns")

async def apply_reset(dut):
    """Apply reset to DUT."""
    await add_wave_marker(dut, "Reset Start")
    dut.rst_n_i.value = 0
    await Timer(RESET_DELAY, units="ns")
    await add_wave_marker(dut, "Reset End")
    dut.rst_n_i.value = 1
    await Timer(CLK_PERIOD, units="ns")

@cocotb.test()
async def test_reset_behavior(dut):
    """Test 1: Reset Behavior Tests"""
    try:
        log.info("Starting reset behavior test")
        
        # Clock setup
        clock = Clock(dut.clk_i, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        # Initialize signals
        await initialize_dut(dut)
        
        # Apply reset and check values
        await apply_reset(dut)
        
        # Verify counter reset to 0
        await RisingEdge(dut.clk_i)
        assert dut.counter.value == 0, f"Counter not reset to 0, got {dut.counter.value}"
        
        # Check output polarity on reset
        assert dut.pwm_o.value == 0, f"PWM output wrong on reset, got {dut.pwm_o.value}"
        
        log.info("Reset behavior test passed")
    except Exception as e:
        log.error(f"Test failed: {str(e)}\n{traceback.format_exc()}")
        raise

@cocotb.test()
async def test_basic_pwm_generation(dut):
    """Test 2: Basic PWM Generation Tests"""
    try:
        log.info("Starting basic PWM generation test")
        
        clock = Clock(dut.clk_i, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        await initialize_dut(dut)
        await apply_reset(dut)
        
        # Enable PWM
        dut.enable_i.value = 1
        
        # Monitor for one complete period
        high_count = 0
        total_count = 0
        
        for _ in range(DEFAULT_PERIOD):
            await RisingEdge(dut.clk_i)
            if dut.pwm_o.value == 1:
                high_count += 1
            total_count += 1
        
        duty_cycle = (high_count / total_count) * 100
        expected_duty = (DEFAULT_DUTY / DEFAULT_PERIOD) * 100
        
        assert abs(duty_cycle - expected_duty) <= 1, f"Duty cycle error: got {duty_cycle}%, expected {expected_duty}%"
        
        log.info("Basic PWM generation test passed")
    except Exception as e:
        log.error(f"Test failed: {str(e)}\n{traceback.format_exc()}")
        raise

@cocotb.test()
async def test_enable_disable_control(dut):
    """Test 3: Enable/Disable Control Tests"""
    try:
        log.info("Starting enable/disable control test")
        
        clock = Clock(dut.clk_i, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        await initialize_dut(dut)
        await apply_reset(dut)
        
        # Test disable state
        dut.enable_i.value = 0
        await RisingEdge(dut.clk_i)
        assert dut.pwm_o.value == 0, "PWM not inactive when disabled"
        
        # Test enable state
        dut.enable_i.value = 1
        await RisingEdge(dut.clk_i)
        
        # Test mid-cycle disable
        await Timer(CLK_PERIOD * 10, units="ns")
        dut.enable_i.value = 0
        await RisingEdge(dut.clk_i)
        assert dut.pwm_o.value == 0, "PWM not returning to inactive state when disabled"
        
        log.info("Enable/disable control test passed")
    except Exception as e:
        log.error(f"Test failed: {str(e)}\n{traceback.format_exc()}")
        raise

@cocotb.test()
async def test_period_control(dut):
    """Test 4: Period Control Tests"""
    try:
        log.info("Starting period control test")
        
        clock = Clock(dut.clk_i, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        await initialize_dut(dut)
        await apply_reset(dut)
        
        # Test period_i = 0 uses DEFAULT_PERIOD
        dut.period_i.value = 0
        dut.enable_i.value = 1
        
        period_count = 0
        last_value = 0
        transitions = 0
        
        # Count transitions for DEFAULT_PERIOD cycles
        for _ in range(DEFAULT_PERIOD * 2):
            await RisingEdge(dut.clk_i)
            if dut.pwm_o.value != last_value:
                transitions += 1
            last_value = dut.pwm_o.value
            period_count += 1
        
        assert transitions > 0, "No PWM transitions detected"
        
        # Test custom period
        test_period = 100
        dut.period_i.value = test_period
        await Timer(CLK_PERIOD * test_period * 2, units="ns")
        
        log.info("Period control test passed")
    except Exception as e:
        log.error(f"Test failed: {str(e)}\n{traceback.format_exc()}")
        raise

@cocotb.test()
async def test_duty_cycle_control(dut):
    """Test 5: Duty Cycle Control Tests"""
    try:
        log.info("Starting duty cycle control test")
        
        clock = Clock(dut.clk_i, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        await initialize_dut(dut)
        await apply_reset(dut)
        
        test_cases = [
            (0, 0),      # 0%
            (64, 25),    # 25%
            (128, 50),   # 50%
            (192, 75),   # 75%
            (255, 100),  # 100%
        ]
        
        for duty, expected_percent in test_cases:
            dut.duty_i[0].value = duty
            dut.enable_i.value = 1
            
            high_count = 0
            total_count = 0
            
            # Monitor for one complete period
            for _ in range(DEFAULT_PERIOD):
                await RisingEdge(dut.clk_i)
                if dut.pwm_o.value == 1:
                    high_count += 1
                total_count += 1
            
            actual_percent = (high_count / total_count) * 100
            assert abs(actual_percent - expected_percent) <= 1, f"Duty cycle error: got {actual_percent}%, expected {expected_percent}%"
        
        log.info("Duty cycle control test passed")
    except Exception as e:
        log.error(f"Test failed: {str(e)}\n{traceback.format_exc()}")
        raise

@cocotb.test()
async def test_edge_cases(dut):
    """Test 7: Edge Cases"""
    try:
        log.info("Starting edge cases test")
        
        clock = Clock(dut.clk_i, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        await initialize_dut(dut)
        await apply_reset(dut)
        
        # Test minimum period value
        dut.period_i.value = 1
        dut.duty_i[0].value = 1
        dut.enable_i.value = 1
        await Timer(CLK_PERIOD * 10, units="ns")
        
        # Test maximum period value
        max_period = (1 << COUNTER_WIDTH) - 1
        dut.period_i.value = max_period
        await Timer(CLK_PERIOD * 10, units="ns")
        
        # Test rapid duty cycle changes
        for _ in range(5):
            dut.duty_i[0].value = random.randint(0, max_period)
            await Timer(CLK_PERIOD * 2, units="ns")
        
        # Test rapid period changes
        for _ in range(5):
            dut.period_i.value = random.randint(1, max_period)
            await Timer(CLK_PERIOD * 2, units="ns")
        
        log.info("Edge cases test passed")
    except Exception as e:
        log.error(f"Test failed: {str(e)}\n{traceback.format_exc()}")
        raise 