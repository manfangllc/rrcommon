import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge, FallingEdge
from cocotb.log import SimLog
import random
import traceback

# Test parameters
CMD_WIDTH = 16
DATA_WIDTH = 8
CLK_PERIOD = 10  # 10ns = 100MHz
SCLK_PERIOD = 40  # 40ns = 25MHz

# Set up module-level logger
log = SimLog("rrspi_test")

class SPIMaster:
    def __init__(self, dut):
        self.dut = dut
        self.sclk = dut.sclk
        self.mosi = dut.mosi
        self.miso = dut.miso
        self.cs_n = dut.cs_n
    
    async def send_bit(self, bit):
        """Send a single bit on MOSI."""
        self.mosi.value = bit
        await RisingEdge(self.sclk)
        log.debug(f"Sent bit: {bit}")
    
    async def read_bit(self):
        """Read a single bit from MISO."""
        await FallingEdge(self.sclk)
        bit = self.miso.value
        log.debug(f"Read bit: {bit}")
        return bit
    
    async def send_command(self, cmd):
        """Send a command word."""
        log.info(f"Sending command: 0x{cmd:04x}")
        self.cs_n.value = 0
        await Timer(SCLK_PERIOD // 4, units="ns")
        
        for i in range(CMD_WIDTH):
            bit = (cmd >> (CMD_WIDTH - 1 - i)) & 1
            await self.send_bit(bit)
        
        await Timer(SCLK_PERIOD // 4, units="ns")
    
    async def send_data(self, data):
        """Send a data byte."""
        log.info(f"Sending data: 0x{data:02x}")
        for i in range(DATA_WIDTH):
            bit = (data >> (DATA_WIDTH - 1 - i)) & 1
            await self.send_bit(bit)
    
    async def read_data(self):
        """Read a data byte."""
        data = 0
        for i in range(DATA_WIDTH):
            bit = await self.read_bit()
            data = (data << 1) | bit
        log.info(f"Read data: 0x{data:02x}")
        return data
    
    async def end_transfer(self):
        """End the SPI transfer."""
        log.debug("Ending transfer")
        self.cs_n.value = 1
        await Timer(SCLK_PERIOD // 4, units="ns")

@cocotb.test()
async def test_rr_spi_slave_reset(dut):
    """Test 1: Reset state verification."""
    try:
        log.info("Starting reset test")
        # Set up clocks
        clk = Clock(dut.clk, CLK_PERIOD, units="ns")
        sclk = Clock(dut.sclk, SCLK_PERIOD, units="ns")
        cocotb.start_soon(clk.start(start_high=False))
        cocotb.start_soon(sclk.start(start_high=False))
        
        # Reset
        log.info("Applying reset")
        dut.rst_n.value = 0
        await Timer(CLK_PERIOD * 5, units="ns")
        dut.rst_n.value = 1
        await Timer(CLK_PERIOD, units="ns")
        
        # Verify reset state
        log.info("Verifying reset state")
        assert dut.cmd_received.value == 0, "cmd_received not cleared after reset"
        assert dut.transfer_done.value == 0, "transfer_done not cleared after reset"
        assert dut.cmd.value == 0, "cmd not cleared after reset"
        assert dut.rx_data.value == 0, "rx_data not cleared after reset"
        log.info("Reset test passed")
    except Exception as e:
        error_msg = f"Reset test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_rr_spi_slave_command(dut):
    """Test 2: Command reception."""
    try:
        log.info("Starting command test")
        # Set up clocks
        clk = Clock(dut.clk, CLK_PERIOD, units="ns")
        sclk = Clock(dut.sclk, SCLK_PERIOD, units="ns")
        cocotb.start_soon(clk.start(start_high=False))
        cocotb.start_soon(sclk.start(start_high=False))
        
        # Reset
        log.info("Applying reset")
        dut.rst_n.value = 0
        await Timer(CLK_PERIOD * 5, units="ns")
        dut.rst_n.value = 1
        await Timer(CLK_PERIOD, units="ns")
        
        # Create SPI master
        spi = SPIMaster(dut)
        
        # Send test command
        test_cmd = 0xA5A5
        await spi.send_command(test_cmd)
        
        # Wait for command to be received
        await Timer(CLK_PERIOD * 2, units="ns")
        
        # Verify command reception
        log.info("Verifying command reception")
        assert dut.cmd_received.value == 1, "cmd_received not asserted after command"
        assert dut.cmd.value == test_cmd, f"Received command mismatch: expected 0x{test_cmd:04x}, got 0x{dut.cmd.value:04x}"
        
        # End transfer
        await spi.end_transfer()
        log.info("Command test passed")
    except Exception as e:
        error_msg = f"Command test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_rr_spi_slave_data_transfer(dut):
    """Test 3: Data transfer."""
    try:
        log.info("Starting data transfer test")
        # Set up clocks
        clk = Clock(dut.clk, CLK_PERIOD, units="ns")
        sclk = Clock(dut.sclk, SCLK_PERIOD, units="ns")
        cocotb.start_soon(clk.start(start_high=False))
        cocotb.start_soon(sclk.start(start_high=False))
        
        # Reset
        log.info("Applying reset")
        dut.rst_n.value = 0
        await Timer(CLK_PERIOD * 5, units="ns")
        dut.rst_n.value = 1
        await Timer(CLK_PERIOD, units="ns")
        
        # Create SPI master
        spi = SPIMaster(dut)
        
        # Send test command
        test_cmd = 0xA5A5
        await spi.send_command(test_cmd)
        
        # Wait for command to be received
        await Timer(CLK_PERIOD * 2, units="ns")
        
        # Set up test data
        test_data = 0x55
        dut.tx_data.value = test_data
        
        # Send test data
        await spi.send_data(test_data)
        
        # Wait for transfer to complete
        await Timer(CLK_PERIOD * 2, units="ns")
        
        # Verify data reception
        log.info("Verifying data reception")
        assert dut.transfer_done.value == 1, "transfer_done not asserted after data transfer"
        assert dut.rx_data.value == test_data, f"Received data mismatch: expected 0x{test_data:02x}, got 0x{dut.rx_data.value:02x}"
        
        # End transfer
        await spi.end_transfer()
        log.info("Data transfer test passed")
    except Exception as e:
        error_msg = f"Data transfer test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_rr_spi_slave_multiple_transfers(dut):
    """Test 4: Multiple transfers."""
    try:
        log.info("Starting multiple transfers test")
        # Set up clocks
        clk = Clock(dut.clk, CLK_PERIOD, units="ns")
        sclk = Clock(dut.sclk, SCLK_PERIOD, units="ns")
        cocotb.start_soon(clk.start(start_high=False))
        cocotb.start_soon(sclk.start(start_high=False))
        
        # Reset
        log.info("Applying reset")
        dut.rst_n.value = 0
        await Timer(CLK_PERIOD * 5, units="ns")
        dut.rst_n.value = 1
        await Timer(CLK_PERIOD, units="ns")
        
        # Create SPI master
        spi = SPIMaster(dut)
        
        # Perform multiple transfers
        for i in range(5):
            log.info(f"Starting transfer {i}")
            # Send command
            test_cmd = random.randint(0, (1 << CMD_WIDTH) - 1)
            await spi.send_command(test_cmd)
            await Timer(CLK_PERIOD * 2, units="ns")
            
            # Verify command
            assert dut.cmd_received.value == 1, f"cmd_received not asserted in transfer {i}"
            assert dut.cmd.value == test_cmd, f"Command mismatch in transfer {i}: expected 0x{test_cmd:04x}, got 0x{dut.cmd.value:04x}"
            
            # Set up and send data
            test_data = random.randint(0, (1 << DATA_WIDTH) - 1)
            dut.tx_data.value = test_data
            await spi.send_data(test_data)
            await Timer(CLK_PERIOD * 2, units="ns")
            
            # Verify data
            assert dut.transfer_done.value == 1, f"transfer_done not asserted in transfer {i}"
            assert dut.rx_data.value == test_data, f"Data mismatch in transfer {i}: expected 0x{test_data:02x}, got 0x{dut.rx_data.value:02x}"
            
            # End transfer
            await spi.end_transfer()
            await Timer(CLK_PERIOD * 2, units="ns")
            log.info(f"Transfer {i} completed successfully")
        
        log.info("Multiple transfers test passed")
    except Exception as e:
        error_msg = f"Multiple transfers test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise 