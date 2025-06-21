/*
 * Copyright (c) 2024
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module spi_peripheral #(
    parameter SPI_MODE = 0
) (
    // Clock/Reset
    input i_rst_n,
    input i_clk,

    // SPI Slave Interface
    input  i_sclk,
    input  i_cs_n,
    input  i_mosi,
    output o_miso,

    // SPI -> PWM Interface
    output [7:0] o_en_reg_out_7_0,   // 0x00
    output [7:0] o_en_reg_out_15_8,  // 0x01
    output [7:0] o_en_reg_pwm_7_0,   // 0x02
    output [7:0] o_en_reg_pwm_15_8,  // 0x03
    output [7:0] o_pwm_duty_cycle    // 0x04
);
  // ================================
  // PWM Control Registers
  // ================================
  reg [7:0] en_reg_out_7_0;  // 0x00
  reg [7:0] en_reg_out_15_8;  // 0x01
  reg [7:0] en_reg_pwm_7_0;  // 0x02
  reg [7:0] en_reg_pwm_15_8;  // 0x03
  reg [7:0] pwm_duty_cycle;  // 0x04

  assign o_en_reg_out_7_0  = en_reg_out_7_0;
  assign o_en_reg_out_15_8 = en_reg_out_15_8;
  assign o_en_reg_pwm_7_0  = en_reg_pwm_7_0;
  assign o_en_reg_pwm_15_8 = en_reg_pwm_15_8;
  assign o_pwm_duty_cycle  = pwm_duty_cycle;

  // ================================
  // CDC Synchronization
  // ================================
  // Level Trigger Signals [N] N = 2
  reg [2:0] mosi_sync;
  reg [3:0] cs_sync;
  // Edge Trigger Signals [N+1] N = 2
  reg [2:0] sclk_sync;

  // Double flopping the input :)
  always @(posedge i_clk or negedge i_rst_n) begin
    if (!i_rst_n) begin
      mosi_sync <= '0;
      cs_sync   <= '1;  // _n
      sclk_sync <= '0;
    end else begin
      mosi_sync <= {i_mosi, mosi_sync[2:1]};
      cs_sync   <= {i_cs_n, cs_sync[3:1]};
      sclk_sync <= {i_sclk, sclk_sync[2:1]};
    end
  end

  // 1 latest -> 0 oldest
  wire stable_mosi, stable_cs;
  wire sclk_posedge, sclk_negedge;
  assign stable_mosi = mosi_sync[0];
  assign stable_cs = cs_sync[0];
  assign sclk_posedge = (sclk_sync[1] == 1'b0) && (sclk_sync[0] == 1'b1);
  assign sclk_negedge = (sclk_sync[1] == 1'b1) && (sclk_sync[0] == 1'b0);

  // ================================
  // SPI
  // ================================
  // SPI Transaction Registers
  reg rw_en;  // 1 - write, 0 - read
  reg [6:0] reg_addr;
  reg [7:0] shift_reg;  // First depo of data

  // SPI State Machine
  typedef enum logic [1:0] {
    RW_BIT  = 2'b00,
    ADDRESS = 2'b01,
    DATA    = 2'b11,
    COMPLETE= 2'b10
  } spi_state_t;

  spi_state_t curr_state, next_state;
  reg [2:0] bit_count;  // counter to determine message end

  wire sclk_slave_read = !SPI_MODE ? sclk_posedge : sclk_negedge;
  // wire sclk_slave_write = SPI_MODE ? sclk_posedge : sclk_negedge;

  // Slave Read, Master Write
  always @(posedge i_clk or negedge i_rst_n) begin
    if (!i_rst_n) begin
      en_reg_out_7_0 <= '0;
      en_reg_out_15_8 <= '0;
      en_reg_pwm_7_0 <= '0;
      en_reg_pwm_15_8 <= '0;
      pwm_duty_cycle <= '0;

      curr_state <= RW_BIT;
      next_state <= RW_BIT;
      bit_count <= 0;
      rw_en <= 1'b0;
      reg_addr <= 7'b0;
      shift_reg <= 8'b0;
    end else begin
      curr_state <= next_state;
      case (curr_state)
        RW_BIT: begin
          if (!stable_cs && sclk_slave_read) begin
            shift_reg <= 8'b0;
            reg_addr <= 7'b0;
            rw_en <= stable_mosi;

            bit_count <= 0;
            next_state <= ADDRESS;
          end else begin
          end
        end

        ADDRESS: begin
          if (!stable_cs) begin
            if (sclk_slave_read) begin
              reg_addr[6-bit_count] <= stable_mosi;
              if (bit_count == 6) begin
                bit_count  <= 0;
                next_state <= DATA;
              end else begin
                bit_count <= bit_count + 1;
              end
            end else begin
            end
          end else begin
            bit_count  <= 0;
            next_state <= RW_BIT;
          end
        end

        DATA: begin
          if (!stable_cs) begin
            if (sclk_slave_read) begin
              shift_reg[7-bit_count] <= stable_mosi;
              if (bit_count == 7) begin
                bit_count  <= 0;
                next_state <= COMPLETE;
              end else begin
                bit_count <= bit_count + 1;
              end
            end else begin
            end
          end else begin
            bit_count  <= 0;
            next_state <= RW_BIT;
          end
        end

        COMPLETE: begin
          if (rw_en) begin  // we are reading
            case (reg_addr)
              'h0: en_reg_out_7_0 <= shift_reg;
              'h1: en_reg_out_15_8 <= shift_reg;
              'h2: en_reg_pwm_7_0 <= shift_reg;
              'h3: en_reg_pwm_15_8 <= shift_reg;
              'h4: pwm_duty_cycle <= shift_reg;
              default: ;
            endcase

            bit_count  <= 0;
            next_state <= RW_BIT;
          end else begin  // they are writing
          end
        end

        default: ;
      endcase
    end
  end

  // Slave Write, Master Read
  assign o_miso = 1'b0;

endmodule
