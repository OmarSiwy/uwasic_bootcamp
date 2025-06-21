
## How it works

This project is intended to display how we can utilize SPI to contorl PWM factors such as **Duty Cycles** and **PWM Frequency**

## How to test

Testing is done using cocotb, where we send an SPI signal and read the PWM frequency and duty as a result of the SPI signal.
- The SPI signal should set the setting to be persistent for this to work. (registers to save setting)

## External hardware

N/A
