/*
 * Copyright (c) 2024 Omar El-Sawy
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_omarsiwy (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);
  assign uio_oe = 8'hFF;  // Set all IOs to output

  // Create wires to refer to the values of the registers
  wire [7:0] en_reg_out_7_0;
  wire [7:0] en_reg_out_15_8;
  wire [7:0] en_reg_pwm_7_0;
  wire [7:0] en_reg_pwm_15_8;
  wire [7:0] pwm_duty_cycle;

  spi_peripheral spi_peripheral_inst (
      .i_rst_n(rst_n),
      .i_clk  (clk),

      .i_sclk(ui_in[0]),
      .i_cs_n(ui_in[2]),
      .i_mosi(ui_in[1]),
      .o_miso(),

      .o_en_reg_out_7_0 (en_reg_out_7_0),
      .o_en_reg_out_15_8(en_reg_out_15_8),
      .o_en_reg_pwm_7_0 (en_reg_pwm_7_0),
      .o_en_reg_pwm_15_8(en_reg_pwm_15_8),
      .o_pwm_duty_cycle (pwm_duty_cycle)
  );

  // Instantiate the PWM module
  pwm_peripheral pwm_peripheral_inst (
      .clk(clk),
      .rst_n(rst_n),
      .en_reg_out_7_0(en_reg_out_7_0),
      .en_reg_out_15_8(en_reg_out_15_8),
      .en_reg_pwm_7_0(en_reg_pwm_7_0),
      .en_reg_pwm_15_8(en_reg_pwm_15_8),
      .pwm_duty_cycle(pwm_duty_cycle),
      .out({uio_out, uo_out})
  );

  wire _unused = &{ena, ui_in[7:3], 1'b0};
endmodule
