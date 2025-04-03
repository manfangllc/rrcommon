import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge, FallingEdge
from cocotb.log import SimLog
import random
import traceback
import os

# Set COCOTB_RESOLVE_X to handle high-impedance values
os.environ['COCOTB_RESOLVE_X'] = 'ZEROS'

# Test parameters
CLK_PERIOD = 10  # 10ns = 100MHz
INIT_DELAY = 50  # Initial delay to allow signals to settle
RESET_DELAY = 50  # Reset hold time
SCLK_PERIOD = 40  # SPI clock period (4x slower than system clock)
CMD_WIDTH = 16
DATA_WIDTH = 8

# Set up module-level logger
log = SimLog("rrspi_test")

async def add_wave_marker(dut, name):
    """Add a marker to the waveform for debugging."""
    log.debug(f"Adding waveform marker: {name}")
    await Timer(1, units="ns")

async def init_spi_idle(dut):
    """Set SPI signals to idle state."""
    try:
        dut.sclk.value = 0
        dut.mosi.value = 0
        dut.cs_n.value = 1
        await Timer(2, units="ns")
    except Exception as e:
        log.error(f"Failed to initialize SPI idle state: {str(e)}")
        raise

async def send_spi_command(dut, command):
    """Send a command over SPI."""
    try:
        log.debug(f"Sending SPI command: 0x{command:04x}")
        await add_wave_marker(dut, f"Command Start: 0x{command:04x}")
        
        # Assert CS
        dut.cs_n.value = 0
        await Timer(CLK_PERIOD * 2, units="ns")  # Wait for state to settle
        
        # Send command bits
        for i in range(CMD_WIDTH-1, -1, -1):
            dut.sclk.value = 0
            dut.mosi.value = (command >> i) & 1
            await Timer(SCLK_PERIOD // 2, units="ns")
            dut.sclk.value = 1
            await Timer(SCLK_PERIOD // 2, units="ns")
            
            # Check for cmd_received on the last bit
            if i == 0:
                await Timer(CLK_PERIOD * 2, units="ns")  # Wait longer for cmd_received
                if dut.cmd_received.value != 1:
                    log.error(f"Command not received after sending all bits")
                    raise AssertionError("cmd_received not asserted after command completion")
        
        await add_wave_marker(dut, "Command Complete")
    except Exception as e:
        log.error(f"Failed to send SPI command: {str(e)}")
        raise

async def send_spi_data(dut, data):
    """Send data over SPI and return received data."""
    try:
        log.debug(f"Sending SPI data: 0x{data:02x}")
        received = 0
        
        # Send/receive data bits
        for i in range(DATA_WIDTH-1, -1, -1):
            dut.sclk.value = 0
            dut.mosi.value = (data >> i) & 1
            await Timer(SCLK_PERIOD // 2, units="ns")
            
            # Sample MISO just before SCLK rising edge
            miso_val = 1 if dut.miso.value == 1 else 0
            dut.sclk.value = 1
            received = (received << 1) | miso_val
            await Timer(SCLK_PERIOD // 2, units="ns")
            
            # Check for transfer_done on the last bit
            if i == 0:
                await Timer(CLK_PERIOD, units="ns")  # Wait one clock cycle for transfer_done
                if dut.transfer_done.value != 1:
                    log.error(f"Transfer not completed after sending all bits")
                    raise AssertionError("transfer_done not asserted after data completion")
        
        return received
    except Exception as e:
        log.error(f"Failed to send/receive SPI data: {str(e)}")
        raise

@cocotb.test()
async def test_reset_behavior(dut):
    """Test reset behavior of the SPI slave."""
    try:
        log.info("Starting reset behavior test")
        
        # Initial setup
        clock = Clock(dut.clk, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        await Timer(INIT_DELAY, units="ns")
        
        # Apply reset
        await add_wave_marker(dut, "Reset Start")
        dut.rst_n.value = 0
        await Timer(RESET_DELAY, units="ns")
        
        # Verify reset state
        assert dut.cmd_received.value == 0, "cmd_received not reset"
        assert dut.cmd.value == 0, "cmd not reset"
        assert dut.rx_data.value == 0, "rx_data not reset"
        assert dut.transfer_done.value == 0, "transfer_done not reset"
        
        # Release reset
        await add_wave_marker(dut, "Reset Release")
        dut.rst_n.value = 1
        await Timer(CLK_PERIOD * 2, units="ns")
        
        log.info("Reset behavior test passed")
    except Exception as e:
        log.error(f"Reset behavior test failed: {str(e)}\n{traceback.format_exc()}")
        raise

@cocotb.test()
async def test_idle_state(dut):
    """Test idle state behavior."""
    try:
        log.info("Starting idle state test")
        
        clock = Clock(dut.clk, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        # Reset sequence
        dut.rst_n.value = 0
        await Timer(RESET_DELAY, units="ns")
        dut.rst_n.value = 1
        await Timer(CLK_PERIOD * 2, units="ns")
        
        # Initialize SPI idle
        await init_spi_idle(dut)
        
        # Toggle SCLK and MOSI in idle state
        for _ in range(5):
            dut.sclk.value = 1
            dut.mosi.value = random.randint(0, 1)
            await Timer(SCLK_PERIOD // 2, units="ns")
            dut.sclk.value = 0
            await Timer(SCLK_PERIOD // 2, units="ns")
            
            # Verify no state changes
            assert dut.cmd_received.value == 0, "Unexpected cmd_received in idle"
            assert dut.transfer_done.value == 0, "Unexpected transfer_done in idle"
        
        log.info("Idle state test passed")
    except Exception as e:
        log.error(f"Idle state test failed: {str(e)}\n{traceback.format_exc()}")
        raise

@cocotb.test()
async def test_basic_command_reception(dut):
    """Test basic command reception."""
    try:
        log.info("Starting basic command reception test")
        
        clock = Clock(dut.clk, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        # Reset sequence
        dut.rst_n.value = 0
        await Timer(RESET_DELAY, units="ns")
        dut.rst_n.value = 1
        await Timer(CLK_PERIOD * 2, units="ns")
        
        # Initialize SPI idle
        await init_spi_idle(dut)
        
        # Send test command
        test_cmd = 0xA55A
        await send_spi_command(dut, test_cmd)
        
        # Verify command value
        assert dut.cmd.value == test_cmd, f"Command mismatch. Expected: 0x{test_cmd:04x}, Got: 0x{dut.cmd.value.integer:04x}"
        
        # Return to idle
        dut.cs_n.value = 1
        await Timer(SCLK_PERIOD, units="ns")
        
        log.info("Basic command reception test passed")
    except Exception as e:
        log.error(f"Basic command reception test failed: {str(e)}\n{traceback.format_exc()}")
        raise

@cocotb.test()
async def test_basic_data_transfer(dut):
    """Test basic data transfer functionality."""
    try:
        log.info("Starting basic data transfer test")
        
        clock = Clock(dut.clk, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        # Reset sequence
        dut.rst_n.value = 0
        await Timer(RESET_DELAY, units="ns")
        dut.rst_n.value = 1
        await Timer(CLK_PERIOD * 2, units="ns")
        
        # Initialize SPI idle
        await init_spi_idle(dut)
        
        # Set up test data
        test_cmd = 0x1234
        test_tx_data = 0x55
        test_rx_data = 0xAA
        
        # Set transmit data
        dut.tx_data.value = test_tx_data
        
        # Send command
        await send_spi_command(dut, test_cmd)
        
        # Send/receive data
        received_data = await send_spi_data(dut, test_rx_data)
        
        # Verify received data
        assert dut.rx_data.value == test_rx_data, f"RX data mismatch. Expected: 0x{test_rx_data:02x}, Got: 0x{dut.rx_data.value.integer:02x}"
        assert received_data == test_tx_data, f"TX data mismatch. Expected: 0x{test_tx_data:02x}, Got: 0x{received_data:02x}"
        assert dut.transfer_done.value == 1, "transfer_done not asserted"
        
        # Return to idle
        dut.cs_n.value = 1
        await Timer(SCLK_PERIOD, units="ns")
        
        log.info("Basic data transfer test passed")
    except Exception as e:
        log.error(f"Basic data transfer test failed: {str(e)}\n{traceback.format_exc()}")
        raise

@cocotb.test()
async def test_cs_n_behavior(dut):
    """Test chip select behavior."""
    try:
        log.info("Starting CS_N behavior test")
        
        clock = Clock(dut.clk, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        # Reset sequence
        dut.rst_n.value = 0
        await Timer(RESET_DELAY, units="ns")
        dut.rst_n.value = 1
        await Timer(CLK_PERIOD * 2, units="ns")
        
        # Test early CS_N deassert during command
        await init_spi_idle(dut)
        dut.cs_n.value = 0
        await Timer(SCLK_PERIOD // 4, units="ns")
        
        # Send partial command
        for i in range(8):  # Only send half the command
            dut.sclk.value = 0
            dut.mosi.value = 1
            await Timer(SCLK_PERIOD // 2, units="ns")
            dut.sclk.value = 1
            await Timer(SCLK_PERIOD // 2, units="ns")
        
        # Early CS_N deassert
        dut.cs_n.value = 1
        await Timer(SCLK_PERIOD, units="ns")
        
        # Verify no command received
        assert dut.cmd_received.value == 0, "Unexpected cmd_received on early CS_N deassert"
        
        log.info("CS_N behavior test passed")
    except Exception as e:
        log.error(f"CS_N behavior test failed: {str(e)}\n{traceback.format_exc()}")
        raise

@cocotb.test()
async def test_back_to_back_transfers(dut):
    """Test back-to-back SPI transfers."""
    try:
        log.info("Starting back-to-back transfer test")
        
        clock = Clock(dut.clk, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        # Reset sequence
        dut.rst_n.value = 0
        await Timer(RESET_DELAY, units="ns")
        dut.rst_n.value = 1
        await Timer(CLK_PERIOD * 2, units="ns")
        
        # Initialize SPI idle
        await init_spi_idle(dut)
        
        # Perform multiple transfers
        for i in range(3):
            test_cmd = 0x1000 | i
            test_tx_data = 0x50 | i
            test_rx_data = 0xA0 | i
            
            # Ensure we're in idle state
            dut.cs_n.value = 1
            await Timer(CLK_PERIOD * 2, units="ns")
            
            dut.tx_data.value = test_tx_data
            
            # Send command and data
            await send_spi_command(dut, test_cmd)
            received_data = await send_spi_data(dut, test_rx_data)
            
            # Verify transfer
            assert dut.cmd.value == test_cmd, f"Command mismatch in transfer {i}"
            assert dut.rx_data.value == test_rx_data, f"RX data mismatch in transfer {i}"
            assert received_data == test_tx_data, f"TX data mismatch in transfer {i}"
            
            # Return to idle with proper delay
            dut.cs_n.value = 1
            await Timer(CLK_PERIOD * 4, units="ns")  # Allow more time for state reset
        
        log.info("Back-to-back transfer test passed")
    except Exception as e:
        log.error(f"Back-to-back transfer test failed: {str(e)}\n{traceback.format_exc()}")
        raise 