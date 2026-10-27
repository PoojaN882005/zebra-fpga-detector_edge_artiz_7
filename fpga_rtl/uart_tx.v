// =============================================================================
// Module: uart_tx.v
// Project: Real-Time FPGA Zebra Crossing Detection System
// Target: Xilinx Artix-7 XC7A35T
//
// Description:
//   Standard 8N1 UART Transmitter with busy and done handshake flags.
// =============================================================================

`timescale 1ns / 1ps

module uart_tx #(
    parameter CLK_FREQ  = 50_000_000,
    parameter BAUD_RATE = 115200
)(
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] data_in,
    input  wire       start,
    output reg        tx,
    output reg        busy,
    output reg        done
);

    localparam CLKS_PER_BIT = CLK_FREQ / BAUD_RATE;

    localparam IDLE  = 2'd0;
    localparam START = 2'd1;
    localparam DATA  = 2'd2;
    localparam STOP  = 2'd3;

    reg [1:0]  state;
    reg [15:0] clk_count;
    reg [2:0]  bit_idx;
    reg [7:0]  tx_shift;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state     <= IDLE;
            tx        <= 1'b1;
            busy      <= 1'b0;
            done      <= 1'b0;
            clk_count <= 16'd0;
            bit_idx   <= 3'd0;
            tx_shift  <= 8'd0;
        end else begin
            done <= 1'b0;

            case (state)
                IDLE: begin
                    tx <= 1'b1;
                    if (start) begin
                        tx_shift  <= data_in;
                        state     <= START;
                        clk_count <= CLKS_PER_BIT - 1;
                        busy      <= 1'b1;
                    end else begin
                        busy <= 1'b0;
                    end
                end

                START: begin
                    tx <= 1'b0; // Start bit
                    if (clk_count == 0) begin
                        state     <= DATA;
                        clk_count <= CLKS_PER_BIT - 1;
                        bit_idx   <= 3'd0;
                    end else begin
                        clk_count <= clk_count - 1'b1;
                    end
                end

                DATA: begin
                    tx <= tx_shift[0]; // LSB first
                    if (clk_count == 0) begin
                        tx_shift  <= {1'b0, tx_shift[7:1]};
                        clk_count <= CLKS_PER_BIT - 1;
                        if (bit_idx == 3'd7) begin
                            state <= STOP;
                        end else begin
                            bit_idx <= bit_idx + 1'b1;
                        end
                    end else begin
                        clk_count <= clk_count - 1'b1;
                    end
                end

                STOP: begin
                    tx <= 1'b1; // Stop bit
                    if (clk_count == 0) begin
                        state <= IDLE;
                        busy  <= 1'b0;
                        done  <= 1'b1;
                    end else begin
                        clk_count <= clk_count - 1'b1;
                    end
                end

                default: state <= IDLE;
            endcase
        end
    end

endmodule
