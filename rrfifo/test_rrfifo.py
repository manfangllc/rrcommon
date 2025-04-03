import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge
from cocotb.log import SimLog
import random
import traceback

# Test parameters
DATA_WIDTH = 8
FIFO_DEPTH = 16
ALMOST_FULL = 12
ALMOST_EMPTY = 4
CLK_PERIOD = 10  # 10ns = 100MHz

# Set up module-level logger
log = SimLog("rrfifo_test")

@cocotb.test()
async def test_rrfifo_reset(dut):
    """Test 1: Verify reset state."""
    try:
        log.info("Starting reset test")
        # Set up clock
        clock = Clock(dut.clk, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        # Reset
        log.info("Applying reset")
        dut.rst_n.value = 0
        await Timer(CLK_PERIOD * 5, units="ns")
        dut.rst_n.value = 1
        await Timer(CLK_PERIOD, units="ns")
        
        # Verify reset state
        log.info("Verifying reset state")
        assert dut.empty_o.value == 1, "Empty flag not asserted after reset"
        assert dut.full_o.value == 0, "Full flag asserted after reset"
        assert dut.almost_full_o.value == 0, "Almost full flag asserted after reset"
        assert dut.almost_empty_o.value == 1, "Almost empty flag not asserted after reset"
        assert dut.overflow_o.value == 0, "Overflow flag asserted after reset"
        assert dut.underflow_o.value == 0, "Underflow flag asserted after reset"
        assert dut.level_o.value == 0, f"Level not zeroed after reset: {dut.level_o.value}"
        log.info("Reset test passed")
    except Exception as e:
        error_msg = f"Reset test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_rrfifo_basic_operations(dut):
    """Test 2: Basic write/read operations."""
    try:
        log.info("Starting basic operations test")
        # Set up clock
        clock = Clock(dut.clk, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        # Reset
        log.info("Applying reset")
        dut.rst_n.value = 0
        await Timer(CLK_PERIOD * 5, units="ns")
        dut.rst_n.value = 1
        await Timer(CLK_PERIOD, units="ns")
        
        # Write 5 values
        log.info("Writing 5 values to FIFO")
        expected_data = []
        for i in range(5):
            test_data = random.randint(0, (1 << DATA_WIDTH) - 1)
            dut.wr_data_i.value = test_data
            dut.wr_en_i.value = 1
            expected_data.append(test_data)
            log.debug(f"Writing data 0x{test_data:02x}")
            await RisingEdge(dut.clk)
            dut.wr_en_i.value = 0
            await RisingEdge(dut.clk)
            
            # Check level
            assert dut.level_o.value == i + 1, f"Level incorrect after write {i}: expected {i+1}, got {dut.level_o.value}"
        
        # Read back 5 values
        log.info("Reading back 5 values from FIFO")
        for i in range(5):
            dut.rd_en_i.value = 1
            await RisingEdge(dut.clk)
            dut.rd_en_i.value = 0
            await RisingEdge(dut.clk)
            
            # Check read data
            expected = expected_data[i]
            assert dut.rd_data_o.value == expected, f"Read data mismatch at index {i}: expected 0x{expected:02x}, got 0x{dut.rd_data_o.value:02x}"
            log.debug(f"Read data 0x{dut.rd_data_o.value:02x}")
            
            # Check level
            assert dut.level_o.value == 4 - i, f"Level incorrect after read {i}: expected {4-i}, got {dut.level_o.value}"
        
        log.info("Basic operations test passed")
    except Exception as e:
        error_msg = f"Basic operations test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_rrfifo_fill_empty(dut):
    """Test 3: Fill to full then empty."""
    try:
        log.info("Starting fill/empty test")
        # Set up clock
        clock = Clock(dut.clk, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        # Reset
        log.info("Applying reset")
        dut.rst_n.value = 0
        await Timer(CLK_PERIOD * 5, units="ns")
        dut.rst_n.value = 1
        await Timer(CLK_PERIOD, units="ns")
        
        # Fill the FIFO
        log.info(f"Filling FIFO to capacity ({FIFO_DEPTH} entries)")
        expected_data = []
        for i in range(FIFO_DEPTH):
            test_data = random.randint(0, (1 << DATA_WIDTH) - 1)
            dut.wr_data_i.value = test_data
            dut.wr_en_i.value = 1
            expected_data.append(test_data)
            log.debug(f"Writing data 0x{test_data:02x}")
            await RisingEdge(dut.clk)
            dut.wr_en_i.value = 0
            await RisingEdge(dut.clk)
            
            # Check full flag on last write
            if i == FIFO_DEPTH - 1:
                assert dut.full_o.value == 1, "Full flag not asserted when FIFO is full"
                log.info("FIFO is full")
        
        # Empty the FIFO
        log.info("Emptying FIFO")
        for i in range(FIFO_DEPTH):
            dut.rd_en_i.value = 1
            await RisingEdge(dut.clk)
            dut.rd_en_i.value = 0
            await RisingEdge(dut.clk)
            
            # Verify read data
            if i > 0:  # Skip first read as it's from previous cycle
                expected = expected_data[i-1]
                assert dut.rd_data_o.value == expected, f"Read data mismatch during emptying at index {i-1}: expected 0x{expected:02x}, got 0x{dut.rd_data_o.value:02x}"
                log.debug(f"Read data 0x{dut.rd_data_o.value:02x}")
            
            # Check empty flag on last read
            if i == FIFO_DEPTH - 1:
                assert dut.empty_o.value == 1, "Empty flag not asserted when FIFO is empty"
                log.info("FIFO is empty")
        
        log.info("Fill/empty test passed")
    except Exception as e:
        error_msg = f"Fill/empty test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_rrfifo_thresholds(dut):
    """Test 4: Test almost full/empty thresholds."""
    try:
        log.info("Starting threshold test")
        # Set up clock
        clock = Clock(dut.clk, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        # Reset
        log.info("Applying reset")
        dut.rst_n.value = 0
        await Timer(CLK_PERIOD * 5, units="ns")
        dut.rst_n.value = 1
        await Timer(CLK_PERIOD, units="ns")
        
        # Fill until almost full
        log.info(f"Filling FIFO until almost full ({ALMOST_FULL} entries)")
        for i in range(ALMOST_FULL):
            test_data = random.randint(0, (1 << DATA_WIDTH) - 1)
            dut.wr_data_i.value = test_data
            dut.wr_en_i.value = 1
            log.debug(f"Writing data 0x{test_data:02x}")
            await RisingEdge(dut.clk)
            dut.wr_en_i.value = 0
            await RisingEdge(dut.clk)
            
            # Check almost full flag
            if i == ALMOST_FULL - 1:
                assert dut.almost_full_o.value == 1, "Almost full flag not asserted at threshold"
                log.info("Almost full threshold reached")
        
        # Empty until almost empty
        log.info(f"Emptying FIFO until almost empty ({ALMOST_EMPTY} entries remaining)")
        for i in range(FIFO_DEPTH - ALMOST_EMPTY):
            dut.rd_en_i.value = 1
            await RisingEdge(dut.clk)
            dut.rd_en_i.value = 0
            await RisingEdge(dut.clk)
            
            # Check almost empty flag
            if i == FIFO_DEPTH - ALMOST_EMPTY - 1:
                assert dut.almost_empty_o.value == 1, "Almost empty flag not asserted at threshold"
                log.info("Almost empty threshold reached")
        
        log.info("Threshold test passed")
    except Exception as e:
        error_msg = f"Threshold test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_rrfifo_overflow(dut):
    """Test 5: Test overflow protection."""
    try:
        log.info("Starting overflow test")
        # Set up clock
        clock = Clock(dut.clk, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        # Reset
        log.info("Applying reset")
        dut.rst_n.value = 0
        await Timer(CLK_PERIOD * 5, units="ns")
        dut.rst_n.value = 1
        await Timer(CLK_PERIOD, units="ns")
        
        # Fill the FIFO
        log.info(f"Filling FIFO to capacity ({FIFO_DEPTH} entries)")
        for i in range(FIFO_DEPTH):
            test_data = random.randint(0, (1 << DATA_WIDTH) - 1)
            dut.wr_data_i.value = test_data
            dut.wr_en_i.value = 1
            log.debug(f"Writing data 0x{test_data:02x}")
            await RisingEdge(dut.clk)
            dut.wr_en_i.value = 0
            await RisingEdge(dut.clk)
        
        # Try to write when full
        test_data = random.randint(0, (1 << DATA_WIDTH) - 1)
        log.info(f"Attempting to write 0x{test_data:02x} to full FIFO")
        dut.wr_data_i.value = test_data
        dut.wr_en_i.value = 1
        await RisingEdge(dut.clk)
        dut.wr_en_i.value = 0
        await RisingEdge(dut.clk)
        
        # Check overflow flag
        assert dut.overflow_o.value == 1, "Overflow flag not asserted when writing to full FIFO"
        log.info("Overflow flag asserted as expected")
        
        log.info("Overflow test passed")
    except Exception as e:
        error_msg = f"Overflow test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_rrfifo_underflow(dut):
    """Test 6: Test underflow protection."""
    try:
        log.info("Starting underflow test")
        # Set up clock
        clock = Clock(dut.clk, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        # Reset
        log.info("Applying reset")
        dut.rst_n.value = 0
        await Timer(CLK_PERIOD * 5, units="ns")
        dut.rst_n.value = 1
        await Timer(CLK_PERIOD, units="ns")
        
        # Try to read when empty
        log.info("Attempting to read from empty FIFO")
        dut.rd_en_i.value = 1
        await RisingEdge(dut.clk)
        dut.rd_en_i.value = 0
        await RisingEdge(dut.clk)
        
        # Check underflow flag
        assert dut.underflow_o.value == 1, "Underflow flag not asserted when reading from empty FIFO"
        log.info("Underflow flag asserted as expected")
        
        log.info("Underflow test passed")
    except Exception as e:
        error_msg = f"Underflow test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_rrfifo_concurrent_rw(dut):
    """Test 7: Concurrent read/write operations."""
    
    # Set up clock
    clock = Clock(dut.clk, CLK_PERIOD, units="ns")
    cocotb.start_soon(clock.start(start_high=False))
    
    # Reset
    dut.rst_n.value = 0
    await Timer(CLK_PERIOD * 5, units="ns")
    dut.rst_n.value = 1
    await Timer(CLK_PERIOD, units="ns")
    
    # Fill FIFO halfway
    for _ in range(FIFO_DEPTH // 2):
        test_data = random.randint(0, (1 << DATA_WIDTH) - 1)
        dut.wr_data_i.value = test_data
        dut.wr_en_i.value = 1
        await RisingEdge(dut.clk)
        dut.wr_en_i.value = 0
        await RisingEdge(dut.clk)
    
    # Perform concurrent read/write operations
    for _ in range(FIFO_DEPTH):
        # Write new data
        test_data = random.randint(0, (1 << DATA_WIDTH) - 1)
        dut.wr_data_i.value = test_data
        dut.wr_en_i.value = 1
        
        # Read data
        dut.rd_en_i.value = 1
        
        await RisingEdge(dut.clk)
        dut.wr_en_i.value = 0
        dut.rd_en_i.value = 0
        await RisingEdge(dut.clk)
        
        # Check that level remains constant
        assert dut.level_o.value == FIFO_DEPTH // 2, f"Level changed during concurrent operations: {dut.level_o.value}" 