// =============================================================================
// Module: uart_rx.v
// Project: Real-Time FPGA Zebra Crossing Detection System
// Target: Xilinx Artix-7 XC7A35T
//
// Description:
//   Standard 8N1 UART Receiver with 2-stage synchronizer for metastability
//   immunity. Samples at the midpoint of each bit.
// =============================================================================

`timescale 1ns / 1ps

module uart_rx #(
    parameter CLK_FREQ  = 50_000_000,
    parameter BAUD_RATE = 115200
)(
    input  wire       clk,
    input  wire       rst_n,
    input  wire       rx,
    output reg  [7:0] data_out,
    output reg        data_valid
);

    localparam CLKS_PER_BIT = CLK_FREQ / BAUD_RATE;  // 434 @ 50MHz/115200

    localparam IDLE  = 2'd0;
    localparam START = 2'd1;
    localparam DATA  = 2'd2;
    localparam STOP  = 2'd3;

    reg [1:0]  state;
    reg [15:0] clk_count;
    reg [2:0]  bit_idx;
    reg [7:0]  rx_shift;
    reg        rx_sync1, rx_sync2;

    // 2-stage synchronizer for async RX input
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rx_sync1 <= 1'b1;
            rx_sync2 <= 1'b1;
        end else begin
            rx_sync1 <= rx;
            rx_sync2 <= rx_sync1;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state      <= IDLE;
            clk_count  <= 16'd0;
            bit_idx    <= 3'd0;
            data_valid <= 1'b0;
            data_out   <= 8'd0;
            rx_shift   <= 8'd0;
        end else begin
            data_valid <= 1'b0;

            case (state)
                IDLE: begin
                    if (rx_sync2 == 1'b0) begin // Start bit detected (falling edge)
                        state     <= START;
                        clk_count <= CLKS_PER_BIT / 2; // Sample at bit center
                    end
                end

                START: begin
                    if (clk_count == 0) begin
                        if (rx_sync2 == 1'b0) begin // Verified valid start bit
                            state     <= DATA;
                            clk_count <= CLKS_PER_BIT - 1;
                            bit_idx   <= 3'd0;
                        end else begin
                            state <= IDLE; // Glitch filter
                        end
                    end else begin
                        clk_count <= clk_count - 1'b1;
                    end
                end

                DATA: begin
                    if (clk_count == 0) begin
                        rx_shift  <= {rx_sync2, rx_shift[7:1]}; // LSB first
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
                    if (clk_count == 0) begin
                        if (rx_sync2 == 1'b1) begin // Valid stop bit
                            data_out   <= rx_shift;
                            data_valid <= 1'b1;
                        end
                        state <= IDLE;
                    end else begin
                        clk_count <= clk_count - 1'b1;
                    end
                end

                default: state <= IDLE;
            endcase
        end
    end

endmodule
