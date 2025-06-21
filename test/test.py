# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from cocotb.types import Logic, LogicArray
from cocotb.utils import get_sim_time

async def detect_rising_edge(dut, signal, bit_index):
    mask = 1 << bit_index
    while (signal.value & mask):
        await ClockCycles(dut.clk, 1)
    while not (signal.value & mask):
        await ClockCycles(dut.clk, 1)

async def detect_falling_edge(dut, signal, bit_index):
    mask = 1 << bit_index
    while not (signal.value & mask):
        await ClockCycles(dut.clk, 1)
    while (signal.value & mask):
        await ClockCycles(dut.clk, 1)

async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def FloatComparison(value1: float, value2: float) -> float:
    return abs(value1 - value2) / value1

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")

@cocotb.test()
async def test_pwm_freq(dut):
    dut._log.info("Start PWM Freq test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # en_reg_pwm_7_0 to get access to out[0]
    dut._log.info("Write transaction, address 0x02, data 0x01")
    await send_spi_transaction(dut, 1, 0x02, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 1000)
    await send_spi_transaction(dut, 1, 0x00, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 1000)

    test_values = [0x0F, 0xD1]
    for test_v in test_values:
        dut._log.info(f"Write transaction, address 0x04, data {test_v}")
        await send_spi_transaction(dut, 1, 0x04, test_v)  # Write transaction
        await ClockCycles(dut.clk, 1000)

        await detect_rising_edge(dut, dut.uo_out, 0)
        start_time = get_sim_time('ns')
        await detect_rising_edge(dut, dut.uo_out, 0)
        end_time = get_sim_time('ns')

        measured_period = end_time - start_time 
        measured_freq = (1 / measured_period)

        dut._log.info(f"{measured_freq}\n")
        assert FloatComparison(measured_freq, 3000), f"Measured Freq: {measured_freq}\nActual Frequency: 3000\n"

    dut._log.info("PWM Frequency test completed successfully")


@cocotb.test()
async def test_pwm_duty(dut):
    dut._log.info("Start PWM Duty test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # en_reg_pwm_7_0 to get access to out[0]
    dut._log.info("Write transaction, address 0x02, data 0x01")
    await send_spi_transaction(dut, 1, 0x02, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 1000)
    await send_spi_transaction(dut, 1, 0x00, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 1000)

    test_values = [0x0F, 0xD1]
    for test_v in test_values:
        dut._log.info("Write transaction, address 0x04, data custom")
        await send_spi_transaction(dut, 1, 0x04, test_v)  # Write transaction
        await ClockCycles(dut.clk, 1000)

        ########################################
        # Track PWM
        ########################################
        await detect_rising_edge(dut, dut.uo_out, 0)
        period_start = get_sim_time('ns')
        await detect_falling_edge(dut, dut.uo_out, 0)
        fall_time = get_sim_time('ns')
        await detect_rising_edge(dut, dut.uo_out, 0)
        period_end = get_sim_time('ns')

        measured_duty_cycle: float = (fall_time - period_start) / (period_end - period_start)
        estimated_duty_cycle: float = (test_v / 0xFF)
        dut._log.info(f"{measured_duty_cycle}\n")
        assert FloatComparison(measured_duty_cycle, estimated_duty_cycle) < 0.10, f"Measured Duty Cycle: {measured_duty_cycle}\nEstimated Duty Cycle: {estimated_duty_cycle}"

    dut._log.info("PWM Duty Cycle test completed successfully")
