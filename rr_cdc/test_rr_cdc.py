import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge, FallingEdge
from cocotb.log import SimLog
from cocotb.result import TestFailure
import random
import traceback

# Test parameters
DATA_WIDTH = 8
NUM_TRANSFERS = 10
CLK_SRC_PERIOD = 10  # 10ns = 100MHz
CLK_DST_PERIOD = 15  # 15ns = ~66.67MHz

# Set up module-level logger
log = SimLog("rr_cdc_test")

async def send_data(dut, data):
    """Helper function to send data in source domain."""
    try:
        # Wait for ready
        while not dut.ready_src_o.value:
            await RisingEdge(dut.clk_src_i)
            log.debug(f"Waiting for ready_src_o, current value: {dut.ready_src_o.value}")
        
        # Apply data and valid
        dut.data_src_i.value = data & ((1 << DATA_WIDTH) - 1)  # Mask to correct width
        dut.valid_src_i.value = 1
        log.debug(f"Sending data: 0x{data:02x}")
        await RisingEdge(dut.clk_src_i)
        dut.valid_src_i.value = 0
    except Exception as e:
        error_msg = f"Error in send_data: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise TestFailure(error_msg)

async def receive_data(dut):
    """Helper function to receive data in destination domain."""
    try:
        # Wait for valid
        while not dut.valid_dst_o.value:
            await RisingEdge(dut.clk_dst_i)
            log.debug(f"Waiting for valid_dst_o, current value: {dut.valid_dst_o.value}")
        
        # Capture data
        data = dut.data_dst_o.value & ((1 << DATA_WIDTH) - 1)  # Mask to correct width
        log.debug(f"Received data: 0x{data:02x}")
        
        # Assert ready to acknowledge receipt
        dut.ready_dst_i.value = 1
        await RisingEdge(dut.clk_dst_i)
        dut.ready_dst_i.value = 0
        
        return data
    except Exception as e:
        error_msg = f"Error in receive_data: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise TestFailure(error_msg)

@cocotb.test()
async def test_rr_cdc_pulse_mode(dut):
    """Test the rr_cdc module in PULSE mode."""
    try:
        # Set up clocks
        clk_src = Clock(dut.clk_src_i, CLK_SRC_PERIOD, units="ns")
        clk_dst = Clock(dut.clk_dst_i, CLK_DST_PERIOD, units="ns")
        cocotb.start_soon(clk_src.start(start_high=False))
        cocotb.start_soon(clk_dst.start(start_high=False))
        
        # Reset
        log.info("Applying reset...")
        dut.rst_src_n_i.value = 0
        dut.rst_dst_n_i.value = 0
        await Timer(100, units="ns")
        dut.rst_src_n_i.value = 1
        dut.rst_dst_n_i.value = 1
        await Timer(100, units="ns")
        log.info("Reset complete")
        
        # Set mode to PULSE
        log.info("Setting mode to PULSE")
        
        # Generate test data
        test_data = [random.randint(0, (1 << DATA_WIDTH) - 1) for _ in range(NUM_TRANSFERS)]
        log.info(f"Generated test data: {[f'0x{x:02x}' for x in test_data]}")
        
        # Start source and destination processes
        async def source_process():
            try:
                for i, data in enumerate(test_data):
                    log.info(f"Source process: Transfer {i}")
                    await send_data(dut, data)
                    await Timer(CLK_SRC_PERIOD * 5, units="ns")
            except Exception as e:
                error_msg = f"Error in source process: {str(e)}\n{traceback.format_exc()}"
                log.error(error_msg)
                raise TestFailure(error_msg)
        
        async def destination_process():
            try:
                received_data = []
                for i in range(NUM_TRANSFERS):
                    log.info(f"Destination process: Transfer {i}")
                    data = await receive_data(dut)
                    received_data.append(data)
                    await Timer(CLK_DST_PERIOD * 5, units="ns")
                
                # Verify received data
                for i, (expected, received) in enumerate(zip(test_data, received_data)):
                    if expected != received:
                        error_msg = f"Transfer {i} mismatch! Expected: 0x{expected:02x}, Got: 0x{received:02x}"
                        log.error(error_msg)
                        raise TestFailure(error_msg)
                    log.info(f"Transfer {i} successful: 0x{received:02x}")
            except Exception as e:
                error_msg = f"Error in destination process: {str(e)}\n{traceback.format_exc()}"
                log.error(error_msg)
                raise TestFailure(error_msg)
        
        # Run both processes concurrently
        await cocotb.start(source_process())
        await cocotb.start(destination_process())
        
        # Wait for completion
        await Timer(1000, units="ns")
    except Exception as e:
        error_msg = f"Test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise TestFailure(error_msg)

@cocotb.test()
async def test_rr_cdc_toggle_mode(dut):
    """Test the rr_cdc module in TOGGLE mode."""
    try:
        # Set up clocks
        clk_src = Clock(dut.clk_src_i, CLK_SRC_PERIOD, units="ns")
        clk_dst = Clock(dut.clk_dst_i, CLK_DST_PERIOD, units="ns")
        cocotb.start_soon(clk_src.start(start_high=False))
        cocotb.start_soon(clk_dst.start(start_high=False))
        
        # Reset
        log.info("Applying reset...")
        dut.rst_src_n_i.value = 0
        dut.rst_dst_n_i.value = 0
        await Timer(100, units="ns")
        dut.rst_src_n_i.value = 1
        dut.rst_dst_n_i.value = 1
        await Timer(100, units="ns")
        log.info("Reset complete")
        
        # Set mode to TOGGLE
        log.info("Setting mode to TOGGLE")
        
        # Generate test data
        test_data = [random.randint(0, (1 << DATA_WIDTH) - 1) for _ in range(NUM_TRANSFERS)]
        log.info(f"Generated test data: {[f'0x{x:02x}' for x in test_data]}")
        
        # Start source and destination processes
        async def source_process():
            try:
                for i, data in enumerate(test_data):
                    log.info(f"Source process: Transfer {i}")
                    await send_data(dut, data)
                    await Timer(CLK_SRC_PERIOD * 5, units="ns")
            except Exception as e:
                error_msg = f"Error in source process: {str(e)}\n{traceback.format_exc()}"
                log.error(error_msg)
                raise TestFailure(error_msg)
        
        async def destination_process():
            try:
                received_data = []
                for i in range(NUM_TRANSFERS):
                    log.info(f"Destination process: Transfer {i}")
                    data = await receive_data(dut)
                    received_data.append(data)
                    await Timer(CLK_DST_PERIOD * 5, units="ns")
                
                # Verify received data
                for i, (expected, received) in enumerate(zip(test_data, received_data)):
                    if expected != received:
                        error_msg = f"Transfer {i} mismatch! Expected: 0x{expected:02x}, Got: 0x{received:02x}"
                        log.error(error_msg)
                        raise TestFailure(error_msg)
                    log.info(f"Transfer {i} successful: 0x{received:02x}")
            except Exception as e:
                error_msg = f"Error in destination process: {str(e)}\n{traceback.format_exc()}"
                log.error(error_msg)
                raise TestFailure(error_msg)
        
        # Run both processes concurrently
        await cocotb.start(source_process())
        await cocotb.start(destination_process())
        
        # Wait for completion
        await Timer(1000, units="ns")
    except Exception as e:
        error_msg = f"Test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise TestFailure(error_msg)

@cocotb.test()
async def test_rr_cdc_handshake_mode(dut):
    """Test the rr_cdc module in HANDSHAKE mode."""
    try:
        # Set up clocks
        clk_src = Clock(dut.clk_src_i, CLK_SRC_PERIOD, units="ns")
        clk_dst = Clock(dut.clk_dst_i, CLK_DST_PERIOD, units="ns")
        cocotb.start_soon(clk_src.start(start_high=False))
        cocotb.start_soon(clk_dst.start(start_high=False))
        
        # Reset
        log.info("Applying reset...")
        dut.rst_src_n_i.value = 0
        dut.rst_dst_n_i.value = 0
        await Timer(100, units="ns")
        dut.rst_src_n_i.value = 1
        dut.rst_dst_n_i.value = 1
        await Timer(100, units="ns")
        log.info("Reset complete")
        
        # Set mode to HANDSHAKE
        log.info("Setting mode to HANDSHAKE")
        
        # Generate test data
        test_data = [random.randint(0, (1 << DATA_WIDTH) - 1) for _ in range(NUM_TRANSFERS)]
        log.info(f"Generated test data: {[f'0x{x:02x}' for x in test_data]}")
        
        # Start source and destination processes
        async def source_process():
            try:
                for i, data in enumerate(test_data):
                    log.info(f"Source process: Transfer {i}")
                    await send_data(dut, data)
                    await Timer(CLK_SRC_PERIOD * 5, units="ns")
            except Exception as e:
                error_msg = f"Error in source process: {str(e)}\n{traceback.format_exc()}"
                log.error(error_msg)
                raise TestFailure(error_msg)
        
        async def destination_process():
            try:
                received_data = []
                for i in range(NUM_TRANSFERS):
                    log.info(f"Destination process: Transfer {i}")
                    data = await receive_data(dut)
                    received_data.append(data)
                    await Timer(CLK_DST_PERIOD * 5, units="ns")
                
                # Verify received data
                for i, (expected, received) in enumerate(zip(test_data, received_data)):
                    if expected != received:
                        error_msg = f"Transfer {i} mismatch! Expected: 0x{expected:02x}, Got: 0x{received:02x}"
                        log.error(error_msg)
                        raise TestFailure(error_msg)
                    log.info(f"Transfer {i} successful: 0x{received:02x}")
            except Exception as e:
                error_msg = f"Error in destination process: {str(e)}\n{traceback.format_exc()}"
                log.error(error_msg)
                raise TestFailure(error_msg)
        
        # Run both processes concurrently
        await cocotb.start(source_process())
        await cocotb.start(destination_process())
        
        # Wait for completion
        await Timer(1000, units="ns")
    except Exception as e:
        error_msg = f"Test failed: {str(e)}\n{traceback.format_exc()}"
        log.error(error_msg)
        raise TestFailure(error_msg) 