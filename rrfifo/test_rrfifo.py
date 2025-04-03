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

async def add_wave_marker(dut, name):
    """Add a marker to the waveform for debugging."""
    log.debug(f"Adding waveform marker: {name}")
    await Timer(1, units="ns")  # Small delay for visibility

# Helper functions
async def reset_dut(dut):
    """Helper function to reset the DUT."""
    try:
        log.info("Starting reset sequence")
        await add_wave_marker(dut, "Reset Start")
        dut.rst_n.value = 0
        await Timer(CLK_PERIOD * 5, units="ns")
        dut.rst_n.value = 1
        await Timer(CLK_PERIOD, units="ns")
        await add_wave_marker(dut, "Reset End")
        log.debug("Reset sequence completed - rst_n: %d", dut.rst_n.value)
        log.info("Reset sequence completed")
    except Exception as e:
        error_msg = f"Reset sequence failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

async def write_data(dut, data):
    """Helper function to write data to FIFO."""
    try:
        await add_wave_marker(dut, f"Write 0x{data:02x}")
        dut.wr_data_i.value = data & ((1 << DATA_WIDTH) - 1)
        dut.wr_en_i.value = 1
        await RisingEdge(dut.clk)
        dut.wr_en_i.value = 0
        await RisingEdge(dut.clk)
        log.debug(f"Wrote data: 0x{data:02x}, level: {int(dut.level_o.value)}, full: {int(dut.full_o.value)}")
    except Exception as e:
        error_msg = f"Write operation failed: {str(e)}\nSignal values: wr_data=0x{data:02x}, level={int(dut.level_o.value)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

async def read_data(dut):
    """Helper function to read data from FIFO."""
    try:
        await add_wave_marker(dut, "Read Operation")
        dut.rd_en_i.value = 1
        await RisingEdge(dut.clk)
        dut.rd_en_i.value = 0
        # Wait for the next clock edge to get the registered data
        await RisingEdge(dut.clk)
        data = int(dut.rd_data_o.value)
        log.debug(f"Read data: 0x{data:02x}, level: {int(dut.level_o.value)}, empty: {int(dut.empty_o.value)}")
        return data
    except Exception as e:
        error_msg = f"Read operation failed: {str(e)}\nSignal values: level={int(dut.level_o.value)}, empty={int(dut.empty_o.value)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_rrfifo_reset(dut):
    """Test 1: Verify reset state."""
    try:
        log.info("Starting reset test")
        await add_wave_marker(dut, "Test Reset Start")
        
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
        await add_wave_marker(dut, "Reset State Verification")
        log.debug(f"Reset state - empty: {dut.empty_o.value}, full: {dut.full_o.value}, level: {dut.level_o.value}")
        assert dut.empty_o.value == 1, f"Empty flag not asserted after reset (value: {dut.empty_o.value})"
        assert dut.full_o.value == 0, f"Full flag asserted after reset (value: {dut.full_o.value})"
        assert dut.almost_full_o.value == 0, f"Almost full flag asserted after reset (value: {dut.almost_full_o.value})"
        assert dut.almost_empty_o.value == 1, f"Almost empty flag not asserted after reset (value: {dut.almost_empty_o.value})"
        assert dut.overflow_o.value == 0, f"Overflow flag asserted after reset (value: {dut.overflow_o.value})"
        assert dut.underflow_o.value == 0, f"Underflow flag asserted after reset (value: {dut.underflow_o.value})"
        assert dut.level_o.value == 0, f"Level not zeroed after reset (value: {dut.level_o.value})"
        await add_wave_marker(dut, "Test Reset End")
        log.info("Reset test passed")
    except Exception as e:
        error_msg = f"Reset test failed: {str(e)}\nSignal values: empty={dut.empty_o.value}, full={dut.full_o.value}, level={dut.level_o.value}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_2_1_single_word(dut):
    """Test 2.1: Write single data word and verify it can be read back."""
    try:
        log.info("Starting Test 2.1: Single word write/read test")
        await add_wave_marker(dut, "Test 2.1 Start")
        
        # Set up clock
        clock = Clock(dut.clk, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        # Reset DUT
        await reset_dut(dut)
        
        # Write single word
        test_data = random.randint(0, (1 << DATA_WIDTH) - 1)
        log.info(f"Writing single word: 0x{test_data:02x}")
        await add_wave_marker(dut, f"Write Single Word 0x{test_data:02x}")
        await write_data(dut, test_data)
        
        # Verify level
        log.debug(f"Checking level - current: {dut.level_o.value}, expected: 1")
        assert dut.level_o.value == 1, f"Level incorrect after write: expected 1, got {dut.level_o.value}"
        
        # Read back and verify
        await add_wave_marker(dut, "Read Back Verification")
        read_value = await read_data(dut)
        log.debug(f"Read verification - read: 0x{read_value:02x}, expected: 0x{test_data:02x}")
        assert read_value == test_data, f"Read data mismatch: expected 0x{test_data:02x}, got 0x{read_value:02x}"
        
        await add_wave_marker(dut, "Test 2.1 End")
        log.info("Test 2.1 passed")
    except Exception as e:
        error_msg = f"Test 2.1 failed: {str(e)}\nSignal values: level={dut.level_o.value}, data=0x{test_data:02x}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_2_2_multiple_words(dut):
    """Test 2.2: Write multiple data words and verify FIFO ordering."""
    try:
        log.info("Starting Test 2.2: Multiple word FIFO ordering test")
        
        # Set up clock
        clock = Clock(dut.clk, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        # Reset DUT
        await reset_dut(dut)
        
        # Write multiple words
        test_data = [random.randint(0, (1 << DATA_WIDTH) - 1) for _ in range(5)]
        log.info(f"Writing {len(test_data)} words")
        for data in test_data:
            await write_data(dut, data)
            
        # Verify level
        assert dut.level_o.value == len(test_data), f"Level incorrect: expected {len(test_data)}, got {dut.level_o.value}"
        
        # Read back and verify order
        for i, expected in enumerate(test_data):
            read_value = await read_data(dut)
            assert read_value == expected, f"Read data mismatch at position {i}: expected 0x{expected:02x}, got 0x{read_value:02x}"
        
        log.info("Test 2.2 passed")
    except Exception as e:
        error_msg = f"Test 2.2 failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_2_3_alternate_rw(dut):
    """Test 2.3: Alternate write and read operations."""
    try:
        log.info("Starting Test 2.3: Alternating read/write test")
        
        # Set up clock
        clock = Clock(dut.clk, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        # Reset DUT
        await reset_dut(dut)
        
        # Perform alternating writes and reads
        for i in range(10):
            # Write operation
            test_data = random.randint(0, (1 << DATA_WIDTH) - 1)
            log.info(f"Write cycle {i}: 0x{test_data:02x}")
            await write_data(dut, test_data)
            
            # Read operation
            read_value = await read_data(dut)
            assert read_value == test_data, f"Read data mismatch in cycle {i}: expected 0x{test_data:02x}, got 0x{read_value:02x}"
            
            # Verify empty after each cycle
            assert dut.empty_o.value == 1, f"FIFO not empty after cycle {i}"
        
        log.info("Test 2.3 passed")
    except Exception as e:
        error_msg = f"Test 2.3 failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_2_4_simultaneous_rw(dut):
    """Test 2.4: Simultaneous read and write operations."""
    try:
        log.info("Starting Test 2.4: Simultaneous read/write test")
        
        # Set up clock
        clock = Clock(dut.clk, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        # Reset DUT
        await reset_dut(dut)
        
        # Write initial data
        initial_data = random.randint(0, (1 << DATA_WIDTH) - 1)
        await write_data(dut, initial_data)
        
        # Perform simultaneous reads and writes
        test_data = [random.randint(0, (1 << DATA_WIDTH) - 1) for _ in range(5)]
        expected_reads = [initial_data] + test_data[:-1]
        
        for i, (test_word, expected_read) in enumerate(zip(test_data, expected_reads)):
            # Set up simultaneous read and write
            dut.wr_data_i.value = test_word
            dut.wr_en_i.value = 1
            dut.rd_en_i.value = 1
            
            # Wait for clock edge
            await RisingEdge(dut.clk)
            
            # Clear enables
            dut.wr_en_i.value = 0
            dut.rd_en_i.value = 0
            
            # Wait for the next clock edge to get the registered read data
            await RisingEdge(dut.clk)
            read_value = int(dut.rd_data_o.value)
            
            assert read_value == expected_read, f"Read data mismatch in cycle {i}: expected 0x{expected_read:02x}, got 0x{read_value:02x}"
            assert int(dut.level_o.value) == 1, f"Incorrect level in cycle {i}: expected 1, got {int(dut.level_o.value)}"
        
        log.info("Test 2.4 passed")
    except Exception as e:
        error_msg = f"Test 2.4 failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise

@cocotb.test()
async def test_2_5_data_integrity(dut):
    """Test 2.5: Verify data integrity across all bit positions."""
    try:
        log.info("Starting Test 2.5: Data integrity test")
        
        # Set up clock
        clock = Clock(dut.clk, CLK_PERIOD, units="ns")
        cocotb.start_soon(clock.start(start_high=False))
        
        # Reset DUT
        await reset_dut(dut)
        
        # Test patterns to check all bits
        test_patterns = [
            0x00,                    # All zeros
            (1 << DATA_WIDTH) - 1,   # All ones
            0x55,                    # Alternating 0/1
            0xAA,                    # Alternating 1/0
            1,                       # Single bit
            1 << (DATA_WIDTH - 1)    # MSB only
        ]
        
        for i, pattern in enumerate(test_patterns):
            # Write pattern
            log.info(f"Testing pattern {i}: 0x{pattern:02x}")
            await write_data(dut, pattern)
            
            # Read back and verify
            read_value = await read_data(dut)
            assert read_value == pattern, f"Data integrity error with pattern 0x{pattern:02x}: got 0x{read_value:02x}"
            
            # Verify empty after each cycle
            assert dut.empty_o.value == 1, f"FIFO not empty after testing pattern {i}"
        
        log.info("Test 2.5 passed")
    except Exception as e:
        error_msg = f"Test 2.5 failed: {str(e)}\n{traceback.format_exc()}"
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
                assert int(dut.full_o.value) == 1, "Full flag not asserted when FIFO is full"
                log.info("FIFO is full")
        
        # Empty the FIFO
        log.info("Emptying FIFO")
        for i in range(FIFO_DEPTH):
            dut.rd_en_i.value = 1
            await RisingEdge(dut.clk)
            read_value = int(dut.rd_data_o.value)
            dut.rd_en_i.value = 0
            await RisingEdge(dut.clk)
            
            # Verify read data
            if i > 0:  # Skip first read as it's from previous cycle
                expected = expected_data[i-1]
                assert read_value == expected, f"Read data mismatch during emptying at index {i-1}: expected 0x{expected:02x}, got 0x{read_value:02x}"
                log.debug(f"Read data 0x{read_value:02x}")
            
            # Check empty flag on last read
            if i == FIFO_DEPTH - 1:
                assert int(dut.empty_o.value) == 1, "Empty flag not asserted when FIFO is empty"
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