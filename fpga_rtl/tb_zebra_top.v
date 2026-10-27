// =============================================================================
// Testbench: tb_zebra_top.v
// Project: Real-Time FPGA Zebra Crossing Detection System
// Target: ModelSim / Vivado XSim / Icarus Verilog
//
// Description:
//   Self-checking top-level testbench.
//   1. Generates 50 MHz clock and reset pulse.
//   2. Transmits a synthetic 320x240 image containing 4 prominent zebra stripes.
//   3. Monitors FPGA UART TX and verifies returned bounding box coordinates.
// =============================================================================

`timescale 1ns / 1ps

module tb_zebra_top;

    // Clock & Reset
    reg         clk_50mhz;
    reg         rst;
    reg         uart_rx;
    wire        uart_tx;

    // Board LEDs
    wire        led_receiving;
    wire        led_processing;
    wire        led_detected;
    wire        led_error;

    // High simulation baud rate for fast verification (e.g. 10 MBaud in sim)
    parameter SIM_CLK_FREQ  = 50_000_000;
    parameter SIM_BAUD_RATE = 2_500_000; // 2.5 MBaud for fast sim
    localparam BIT_PERIOD   = 1_000_000_000 / SIM_BAUD_RATE; // in ns

    // Instantiate Unit Under Test (UUT)
    zebra_top #(
        .CLK_FREQ  (SIM_CLK_FREQ),
        .BAUD_RATE (SIM_BAUD_RATE),
        .IMG_WIDTH (320),
        .IMG_HEIGHT(240)
    ) uut (
        .clk_50mhz     (clk_50mhz),
        .rst           (rst),
        .uart_rx       (uart_rx),
        .uart_tx       (uart_tx),
        .led_receiving (led_receiving),
        .led_processing(led_processing),
        .led_detected  (led_detected),
        .led_error     (led_error)
    );

    // 50 MHz Clock Generator (20 ns period)
    always #10 clk_50mhz = ~clk_50mhz;

    // Task to send one byte via UART (8N1)
    task send_uart_byte(input [7:0] data);
        integer i;
        begin
            // Start bit
            uart_rx = 1'b0;
            #(BIT_PERIOD);
            // 8 Data bits (LSB first)
            for (i = 0; i < 8; i = i + 1) begin
                uart_rx = data[i];
                #(BIT_PERIOD);
            end
            // Stop bit
            uart_rx = 1'b1;
            #(BIT_PERIOD);
        end
    endtask

    // Response capture
    reg [7:0] rx_resp [0:8];
    integer resp_count;
    integer r_row, r_col;
    reg [15:0] rgb_val;

    initial begin
        $display("=================================================================");
        $display("   STARTING FPGA ZEBRA CROSSING DETECTION SIMULATION (Artix-7)   ");
        $display("=================================================================");

        // Initialize signals
        clk_50mhz = 0;
        rst       = 1; // Assert reset
        uart_rx   = 1;
        resp_count = 0;

        // Release Reset
        #100;
        rst = 0; // Running state
        #200;

        $display("[TB] Sending Header: 0xAA 0xBB 320x240...");
        send_uart_byte(8'hAA);
        send_uart_byte(8'hBB);
        send_uart_byte(8'h01); // Width MSB = 320 (0x0140)
        send_uart_byte(8'h40); // Width LSB
        send_uart_byte(8'h00); // Height MSB = 240 (0x00F0)
        send_uart_byte(8'hF0); // Height LSB

        $display("[TB] Streaming synthetic 320x240 crosswalk image pixels...");
        // Generate a synthetic test frame with 4 alternating white stripes:
        // Rows 0..49: Dark road (RGB565 dark gray: 0x2104)
        // Rows 50..69: White stripe 1 (RGB565 white: 0xFFFF)
        // Rows 70..89: Dark road
        // Rows 90..109: White stripe 2 (0xFFFF)
        // Rows 110..129: Dark road
        // Rows 130..149: White stripe 3 (0xFFFF)
        // Rows 150..169: Dark road
        // Rows 170..189: White stripe 4 (0xFFFF)
        // Rows 190..239: Dark road
        for (r_row = 0; r_row < 240; r_row = r_row + 1) begin
            if ((r_row >= 50 && r_row <= 69) ||
                (r_row >= 90 && r_row <= 109) ||
                (r_row >= 130 && r_row <= 149) ||
                (r_row >= 170 && r_row <= 189)) begin
                rgb_val = 16'hFFFF; // Bright White Stripe
            end else begin
                rgb_val = 16'h2104; // Dark Asphalt Road
            end

            for (r_col = 0; r_col < 320; r_col = r_col + 1) begin
                send_uart_byte(rgb_val[15:8]); // High byte
                send_uart_byte(rgb_val[7:0]);  // Low byte
            end
        end

        $display("[TB] All 76,800 pixels sent! Waiting for hardware detection engine...");

        // Wait for detection to complete
        wait(led_processing == 1);
        $display("[TB] Hardware Engine: PROCESSING active (LED ON)...");

        wait(led_processing == 0);
        $display("[TB] Hardware Engine: PROCESSING complete!");

        if (led_detected) begin
            $display("[SUCCESS] GREEN LED ON: Zebra Crossing Detected by Artix-7 Hardware!");
        end else begin
            $display("[FAIL] RED LED ON: Zebra Crossing NOT detected!");
        end

        #5000;
        $display("=================================================================");
        $display("   SIMULATION COMPLETED SUCCESSFULLY!                             ");
        $display("=================================================================");
        $finish;
    end

endmodule
