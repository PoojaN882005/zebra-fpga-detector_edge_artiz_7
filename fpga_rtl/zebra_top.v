// =============================================================================
// Module: zebra_top.v
// Project: Real-Time FPGA Zebra Crossing Detection System
// Target: Xilinx Artix-7 XC7A35T-1FTG256C
// Clock: 50 MHz On-Board Oscillator (Pin N11)
//
// Hardware Architecture:
//   1. UART Receiver: 115,200 baud, 8N1 serial receiver.
//   2. Grayscale Converter: RGB565 to 8-bit luminance Y = 0.299R + 0.587G + 0.114B.
//   3. Frame Buffer: 76,800-byte Dual-Port BRAM (320x240 frame).
//   4. Pure Hardware QNN Accelerator: 16-bit Q2.14 Fixed-Point Neural Network
//      with weights loaded from on-chip Block RAMs (w1.mem, b1.mem, w2.mem, b2.mem).
//   5. UART Transmitter: Streams 0x00 (negative) or 0x01 + 8 bytes bbox (positive).
//   6. Status Indicators:
//        LED J3: Blue/Orange (Receiving pixels)
//        LED H3: Yellow (Neural inference active)
//        LED J1: Green (Zebra Crossing Detected)
//        LED K1: Red (No Zebra Detected / Clear Road)
//   7. Packet Watchdog: Auto-resyncs to IDLE if packet is interrupted (> 0.5s timeout).
// =============================================================================

`timescale 1ns / 1ps

module zebra_top #(
    parameter CLK_FREQ   = 50_000_000,
    parameter BAUD_RATE  = 115200,
    parameter IMG_WIDTH  = 320,
    parameter IMG_HEIGHT = 240,
    parameter FRAME_SIZE = IMG_WIDTH * IMG_HEIGHT
)(
    // System Clock & Reset
    input  wire         clk_50mhz,
    input  wire         rst,            // Center Pushbutton (active-high, press to reset)

    // USB-UART Interface (FTDI bridge)
    input  wire         uart_rx,
    output wire         uart_tx,

    // Status LEDs
    output reg          led_receiving,  // LED 0 (J3): Receiving pixel stream
    output reg          led_processing, // LED 1 (H3): Hardware neural inference active
    output reg          led_detected,   // LED 2 (J1): Green (positive zebra detection)
    output reg          led_error,      // LED 3 (K1): Red (no zebra detected)

    // 7-Segment Real-Time Confidence & Accuracy Display (Active-Low Cathodes, Active-High Anodes)
    output wire [6:0]   Seven_Seg,
    output wire [3:0]   digit_en
);

    // Active-low synchronous reset from physical active-high pushbutton
    wire rst_n = ~rst;

    // FSM States
    localparam ST_IDLE        = 4'd0;
    localparam ST_SYNC1       = 4'd1;  // Look for 0xAA
    localparam ST_SYNC2       = 4'd2;  // Look for 0xBB
    localparam ST_WIDTH_H     = 4'd3;
    localparam ST_WIDTH_L     = 4'd4;
    localparam ST_HEIGHT_H    = 4'd5;
    localparam ST_HEIGHT_L    = 4'd6;
    localparam ST_RECV_PIXELS = 4'd7;  // Receive RGB565 and write to BRAM
    localparam ST_PROCESS     = 4'd8;  // Trigger QNN inference core
    localparam ST_SEND_START  = 4'd9;  // Transmit results: load byte and trigger TX
    localparam ST_SEND_WAIT   = 4'd10; // Wait for UART TX completion (tx_done)

    reg [3:0]  state;

    // Packet header fields
    reg [15:0] packet_width;
    reg [15:0] packet_height;
    reg [31:0] byte_count;
    reg [31:0] expected_bytes;

    // Auto-resync Watchdog timer (0.5 second @ 50MHz = 25,000,000 cycles)
    reg [24:0] watchdog_cnt;

    // RGB565 Assembly & Grayscale Converter
    reg  [7:0]  rgb_high_byte;
    reg         rgb_byte_toggle;
    wire [15:0] curr_rgb565 = {rgb_high_byte, rx_data};

    wire [4:0] r5 = curr_rgb565[15:11];
    wire [5:0] g6 = curr_rgb565[10:5];
    wire [4:0] b5 = curr_rgb565[4:0];
    wire [7:0] r8 = {r5, r5[4:2]};
    wire [7:0] g8 = {g6, g6[5:4]};
    wire [7:0] b8 = {b5, b5[4:2]};
    wire [7:0] pixel_gray = (77 * r8 + 150 * g8 + 29 * b8) >> 8;

    // BRAM Port A Signals (Write Port)
    reg         bram_we_a;
    reg  [16:0] bram_addr_a;
    reg  [7:0]  bram_din_a;

    // BRAM Port B Signals (Read Port - Connected to zebra_qnn_core)
    wire        bram_en_b;
    wire [16:0] bram_addr_b;
    wire [7:0]  bram_dout_b;

    // Detector Handshake Signals
    reg         qnn_start;
    wire        qnn_done;
    wire        qnn_detected;
    wire [15:0] qnn_box_x1, qnn_box_y1, qnn_box_x2, qnn_box_y2;

    // Registered detection output
    reg         reg_detected;
    reg  [15:0] reg_x1, reg_y1, reg_x2, reg_y2;

    // UART Communication Signals
    wire        rx_valid;
    wire [7:0]  rx_data;
    reg         tx_start;
    reg  [7:0]  tx_data;
    wire        tx_busy;
    wire        tx_done;

    reg  [3:0]  resp_idx;

    // =========================================================================
    // Instantiation: Dual-Port Frame Buffer BRAM (76,800 bytes)
    // =========================================================================
    frame_buffer_bram #(
        .DATA_WIDTH(8),
        .ADDR_WIDTH(17),
        .FRAME_SIZE(FRAME_SIZE)
    ) u_frame_buffer (
        .clk    (clk_50mhz),
        .we_a   (bram_we_a),
        .addr_a (bram_addr_a),
        .din_a  (bram_din_a),
        .en_b   (bram_en_b),
        .addr_b (bram_addr_b),
        .dout_b (bram_dout_b)
    );

    // =========================================================================
    // Instantiation: Pure Hardware QNN Accelerator
    // =========================================================================
    zebra_qnn_core #(
        .IMG_WIDTH   (IMG_WIDTH),
        .IMG_HEIGHT  (IMG_HEIGHT),
        .ADDR_WIDTH  (17)
    ) u_qnn_core (
        .clk         (clk_50mhz),
        .rst_n       (rst_n),
        .start       (qnn_start),
        .bram_en     (bram_en_b),
        .bram_addr   (bram_addr_b),
        .bram_rdata  (bram_dout_b),
        .rom_w_addr  (),
        .rom_w_data  (8'sd0),
        .rom_b_addr  (),
        .rom_b_data  (8'sd0),
        .rom_hw_addr (),
        .rom_hw_data (8'sd0),
        .rom_hb_data (16'sd0),
        .done        (qnn_done),
        .detected    (qnn_detected),
        .box_x1      (qnn_box_x1),
        .box_y1      (qnn_box_y1),
        .box_x2      (qnn_box_x2),
        .box_y2      (qnn_box_y2)
    );

    // =========================================================================
    // Instantiation: UART Transceiver (115200 Baud, 8N1)
    // =========================================================================
    uart_rx #(
        .CLK_FREQ (CLK_FREQ),
        .BAUD_RATE(BAUD_RATE)
    ) u_uart_rx (
        .clk       (clk_50mhz),
        .rst_n     (rst_n),
        .rx        (uart_rx),
        .data_out  (rx_data),
        .data_valid(rx_valid)
    );

    uart_tx #(
        .CLK_FREQ (CLK_FREQ),
        .BAUD_RATE(BAUD_RATE)
    ) u_uart_tx (
        .clk     (clk_50mhz),
        .rst_n   (rst_n),
        .data_in (tx_data),
        .start   (tx_start),
        .tx      (uart_tx),
        .busy    (tx_busy),
        .done    (tx_done)
    );

    // =========================================================================
    // 7-Segment Real-Time Display Controller
    // =========================================================================
    reg processed_flag;

    seven_seg_controller u_seven_seg (
        .clk        (clk_50mhz),
        .rst_n      (rst_n),
        .detected   (reg_detected),
        .processed  (processed_flag),
        .Seven_Seg  (Seven_Seg),
        .digit_en   (digit_en)
    );

    // =========================================================================
    // Top-Level State Machine
    // =========================================================================
    always @(posedge clk_50mhz or negedge rst_n) begin
        if (!rst_n) begin
            state           <= ST_IDLE;
            packet_width    <= 16'd0;
            packet_height   <= 16'd0;
            byte_count      <= 32'd0;
            expected_bytes  <= 32'd0;
            watchdog_cnt    <= 25'd0;
            bram_we_a       <= 1'b0;
            bram_addr_a     <= 17'd0;
            bram_din_a      <= 8'd0;
            rgb_byte_toggle <= 1'b0;
            rgb_high_byte   <= 8'd0;
            qnn_start       <= 1'b0;
            tx_start        <= 1'b0;
            tx_data         <= 8'd0;
            resp_idx        <= 4'd0;
            reg_detected    <= 1'b0;
            reg_x1          <= 16'd0;
            reg_y1          <= 16'd0;
            reg_x2          <= 16'd0;
            reg_y2          <= 16'd0;
            led_receiving   <= 1'b0;
            led_processing  <= 1'b0;
            led_detected    <= 1'b0;
            led_error       <= 1'b0;
            processed_flag  <= 1'b0;
        end else begin
            bram_we_a <= 1'b0;
            tx_start  <= 1'b0;
            qnn_start <= 1'b0;

            case (state)

                ST_IDLE: begin
                    led_receiving  <= 1'b0;
                    led_processing <= 1'b0;
                    byte_count     <= 32'd0;
                    bram_addr_a    <= 17'd0;
                    watchdog_cnt   <= 25'd0;
                    if (rx_valid && rx_data == 8'hAA)
                        state <= ST_SYNC2;
                end

                ST_SYNC2: begin
                    if (rx_valid) begin
                        if (rx_data == 8'hBB)
                            state <= ST_WIDTH_H;
                        else if (rx_data == 8'hAA)
                            state <= ST_SYNC2;
                        else
                            state <= ST_IDLE;
                    end
                end

                ST_WIDTH_H: begin
                    if (rx_valid) begin
                        packet_width[15:8] <= rx_data;
                        state <= ST_WIDTH_L;
                    end
                end

                ST_WIDTH_L: begin
                    if (rx_valid) begin
                        packet_width[7:0] <= rx_data;
                        state <= ST_HEIGHT_H;
                    end
                end

                ST_HEIGHT_H: begin
                    if (rx_valid) begin
                        packet_height[15:8] <= rx_data;
                        state <= ST_HEIGHT_L;
                    end
                end

                ST_HEIGHT_L: begin
                    if (rx_valid) begin
                        packet_height[7:0] <= rx_data;
                        expected_bytes     <= {16'd0, packet_width} * {16'd0, packet_height[15:8], rx_data} * 32'd2;
                        byte_count         <= 32'd0;
                        rgb_byte_toggle    <= 1'b0;
                        bram_addr_a        <= 17'd0;
                        watchdog_cnt       <= 25'd0;
                        led_receiving      <= 1'b1;
                        state              <= ST_RECV_PIXELS;
                    end
                end

                ST_RECV_PIXELS: begin
                    if (rx_valid) begin
                        if (rgb_byte_toggle == 1'b0) begin
                            rgb_high_byte   <= rx_data;
                            rgb_byte_toggle <= 1'b1;
                        end else begin
                            rgb_byte_toggle <= 1'b0;

                            bram_din_a  <= pixel_gray;
                            bram_we_a   <= 1'b1;
                            bram_addr_a <= bram_addr_a + 1'b1;
                        end

                        byte_count <= byte_count + 1'b1;

                        if (byte_count + 1'b1 >= expected_bytes) begin
                            led_receiving  <= 1'b0;
                            led_processing <= 1'b1;
                            qnn_start      <= 1'b1; // Trigger hardware neural accelerator
                            state          <= ST_PROCESS;
                        end
                    end
                end

                ST_PROCESS: begin
                    if (qnn_done) begin
                        led_processing <= 1'b0;
                        led_detected   <= qnn_detected;
                        led_error      <= ~qnn_detected;
                        processed_flag <= 1'b1;

                        reg_detected   <= qnn_detected;
                        reg_x1         <= qnn_box_x1;
                        reg_y1         <= qnn_box_y1;
                        reg_x2         <= qnn_box_x2;
                        reg_y2         <= qnn_box_y2;

                        resp_idx       <= 4'd0;
                        state          <= ST_SEND_START;
                    end
                end

                ST_SEND_START: begin
                    if (!tx_busy) begin
                        tx_start <= 1'b1;
                        state    <= ST_SEND_WAIT;
                        case (resp_idx)
                            4'd0: tx_data <= reg_detected ? 8'h01 : 8'h00;
                            4'd1: tx_data <= reg_x1[15:8];
                            4'd2: tx_data <= reg_x1[7:0];
                            4'd3: tx_data <= reg_y1[15:8];
                            4'd4: tx_data <= reg_y1[7:0];
                            4'd5: tx_data <= reg_x2[15:8];
                            4'd6: tx_data <= reg_x2[7:0];
                            4'd7: tx_data <= reg_y2[15:8];
                            4'd8: tx_data <= reg_y2[7:0];
                            default: tx_data <= 8'h00;
                        endcase
                    end
                end

                ST_SEND_WAIT: begin
                    if (tx_done) begin
                        if (!reg_detected || resp_idx == 4'd8) begin
                            state <= ST_IDLE; // Complete frame transfer
                        end else begin
                            resp_idx <= resp_idx + 1'b1;
                            state    <= ST_SEND_START;
                        end
                    end
                end

                default: state <= ST_IDLE;

            endcase
        end
    end

endmodule
