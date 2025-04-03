import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge, FallingEdge
from cocotb.log import SimLog
import random
import traceback

# Test parameters
COUNTER_WIDTH = 8
NUM_CHANNELS = 1  # Changed from 4 to 1 to match module default
CLK_PERIOD = 10  # 10ns = 100MHz
DEFAULT_PERIOD = 255
DEFAULT_DUTY = 128

# Set up module-level logger
log = SimLog("rrpwm_test")

async def measure_pwm(dut, channel, period, cycles):
    """Measure PWM duty cycle for a channel."""
    log.debug(f"Measuring PWM duty cycle for channel {channel}")
    high_count = 0
    period_count = 0
    
    # Measure for the specified number of complete periods
    for cycle in range(cycles):
        log.debug(f"Starting measurement cycle {cycle}")
        # Wait for rising edge
        while not dut.pwm_o.value:  # Changed from pwm_o[channel] to pwm_o
            await RisingEdge(dut.clk_i)
        
        # Count through one complete period
        while period_count < period:
            await RisingEdge(dut.clk_i)
            period_count += 1
            if dut.pwm_o.value:  # Changed from pwm_o[channel] to pwm_o
                high_count += 1
        
        # Reset period counter for next cycle
        period_count = 0
    
    # Calculate measured duty cycle
    measured_duty = high_count / period
    log.debug(f"Measured duty cycle: {measured_duty:.3f}")

    return measured_duty

@cocotb.test()
async def test_rrpwm_basic(dut):
    """Test 1: Basic operation - Enable channel 0 with 50% duty cycle."""
    try:
        log.info("Starting basic PWM test")
        # Set up clock
        clock = Clock(dut.clk_i, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        # Reset
        log.info("Applying reset")
        dut.rst_n_i.value = 0
        await Timer(CLK_PERIOD * 2, units="ns")
        dut.rst_n_i.value = 1
        await Timer(CLK_PERIOD * 2, units="ns")
        
        # Set up test parameters
        period = 100  # Set period to 100 clock cycles
        dut.period_i.value = period
        dut.enable_i.value = 0  # Disable all channels initially
        
        # Set duty cycle for channel 0 to 50%
        duty = 50
        dut.duty_i.value = duty  # Changed from duty_i[0] to duty_i
        
        # Enable channel 0
        log.info(f"Enabling channel with period={period}, duty={duty}")
        dut.enable_i.value = 1
        
        # Wait for 3 periods
        await Timer(CLK_PERIOD * period * 3, units="ns")
        
        # Measure duty cycle
        measured_duty = await measure_pwm(dut, 0, period, 1)
        
        # Expected duty ratio
        expected_duty = duty / period
        
        # Check if duty cycle is within tolerance
        tolerance = 0.01  # 1% tolerance
        assert abs(measured_duty - expected_duty) <= tolerance, \
            f"Channel 0 duty cycle mismatch. Expected: {expected_duty:.3f}, Measured: {measured_duty:.3f}"
        log.info("Basic PWM test passed")
    except Exception as e:
        error_msg = f"Basic PWM test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_rrpwm_duty_update(dut):
    """Test 2: Change duty cycle during operation."""
    try:
        log.info("Starting duty cycle update test")
        # Set up clock
        clock = Clock(dut.clk_i, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        # Reset
        log.info("Applying reset")
        dut.rst_n_i.value = 0
        await Timer(CLK_PERIOD * 2, units="ns")
        dut.rst_n_i.value = 1
        await Timer(CLK_PERIOD * 2, units="ns")
        
        # Set up test parameters
        period = 100
        dut.period_i.value = period
        dut.enable_i.value = 1  # Enable channel 0
        
        # Start with 50% duty cycle
        log.info("Setting initial duty cycle to 50%")
        dut.duty_i.value = 50  # Changed from duty_i[0] to duty_i
        await Timer(CLK_PERIOD * period * 3, units="ns")
        
        # Change to 80% duty cycle
        log.info("Updating duty cycle to 80%")
        dut.duty_i.value = 80  # Changed from duty_i[0] to duty_i
        await Timer(CLK_PERIOD * period * 3, units="ns")
        
        # Measure new duty cycle
        measured_duty = await measure_pwm(dut, 0, period, 1)
        expected_duty = 80 / period
        tolerance = 0.01  # 1% tolerance
        
        assert abs(measured_duty - expected_duty) <= tolerance, \
            f"Duty cycle mismatch after update. Expected: {expected_duty:.3f}, Measured: {measured_duty:.3f}"
        log.info("Duty cycle update test passed")
    except Exception as e:
        error_msg = f"Duty cycle update test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_rrpwm_period_update(dut):
    """Test 3: Change period during operation."""
    try:
        log.info("Starting period update test")
        # Set up clock
        clock = Clock(dut.clk_i, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        # Reset
        log.info("Applying reset")
        dut.rst_n_i.value = 0
        await Timer(CLK_PERIOD * 2, units="ns")
        dut.rst_n_i.value = 1
        await Timer(CLK_PERIOD * 2, units="ns")
        
        # Set up test parameters
        period = 100
        dut.period_i.value = period
        dut.enable_i.value = 1  # Enable channel 0
        
        # Start with 50% duty cycle
        log.info("Setting initial period to 100 and duty cycle to 50%")
        dut.duty_i.value = 50  # Changed from duty_i[0] to duty_i
        await Timer(CLK_PERIOD * period * 3, units="ns")
        
        # Change period to 200 and adjust duty cycle
        period = 200
        log.info(f"Updating period to {period} and adjusting duty cycle")
        dut.period_i.value = period
        dut.duty_i.value = 100  # 50% of new period
        await Timer(CLK_PERIOD * period * 3, units="ns")
        
        # Measure new duty cycle
        measured_duty = await measure_pwm(dut, 0, period, 1)
        expected_duty = 100 / period  # Should still be 50%
        tolerance = 0.01  # 1% tolerance
        
        assert abs(measured_duty - expected_duty) <= tolerance, \
            f"Duty cycle mismatch after period change. Expected: {expected_duty:.3f}, Measured: {measured_duty:.3f}"
        log.info("Period update test passed")
    except Exception as e:
        error_msg = f"Period update test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_rrpwm_enable_disable(dut):
    """Test 4: Test enable/disable functionality."""
    try:
        log.info("Starting enable/disable test")
        # Set up clock
        clock = Clock(dut.clk_i, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        # Reset
        log.info("Applying reset")
        dut.rst_n_i.value = 0
        await Timer(CLK_PERIOD * 2, units="ns")
        dut.rst_n_i.value = 1
        await Timer(CLK_PERIOD * 2, units="ns")
        
        # Set up test parameters
        period = 100
        dut.period_i.value = period
        dut.duty_i.value = 50  # Changed from duty_i[0] to duty_i
        
        # Enable channel
        log.info("Enabling channel")
        dut.enable_i.value = 1
        await Timer(CLK_PERIOD * period * 3, units="ns")
        
        # Disable channel
        log.info("Disabling channel")
        dut.enable_i.value = 0
        await Timer(CLK_PERIOD * period * 3, units="ns")
        
        # Check that output is inactive
        assert dut.pwm_o.value == 0, "Output should be inactive when disabled"
        log.info("Enable/disable test passed")
    except Exception as e:
        error_msg = f"Enable/disable test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise 