// =============================================================================
// Module: seven_seg_controller.v
// Target: EDGE Artix-7 FPGA (XC7A35T-1FTG256C)
// Description:
//   Multiplexed 4-Digit 7-Segment Display Controller for Real-Time Zebra Detection.
//   Cathodes: Active-Low (A..G) on pins G2, G1, H5, H4, J5, J4, H2
//   Anodes:   Active-High (digit_en[3:0]) on pins F2, E1, G5, G4
//
// Display Modes:
//   1. IDLE / READY (before first image): Displays "rdy "
//   2. ZEBRA DETECTED:                    Displays "d100" (Detected, 100% Match)
//   3. NO ZEBRA / CLEAR ROAD:             Displays "no00" (No Crosswalk, 0%)
// =============================================================================

`timescale 1ns / 1ps

module seven_seg_controller (
    input  wire       clk,        // 50 MHz system clock
    input  wire       rst_n,      // Active-low synchronous reset
    input  wire       detected,   // Latched FPGA classification decision
    input  wire       processed,  // Latched flag indicating frame evaluated
    output reg  [6:0] Seven_Seg,  // Active-Low Cathodes (A, B, C, D, E, F, G)
    output reg  [3:0] digit_en    // Active-High Anodes  (Digit 0, 1, 2, 3)
);

    // Refresh clock divider: 50 MHz / 50,000 = 1 kHz refresh rate across 4 digits
    reg [15:0] clk_div;
    reg [1:0]  digit_sel;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            clk_div   <= 16'd0;
            digit_sel <= 2'd0;
        end else begin
            if (clk_div == 16'd49999) begin
                clk_div   <= 16'd0;
                digit_sel <= digit_sel + 1'b1;
            end else begin
                clk_div <= clk_div + 1'b1;
            end
        end
    end

    // Pattern definitions (Active-Low: 0 = LED segment ON, 1 = OFF)
    // Seven_Seg = {G, F, E, D, C, B, A}
    localparam PAT_BLANK = 7'b1111111;
    localparam PAT_0     = 7'b1000000; // '0'
    localparam PAT_1     = 7'b1111001; // '1'
    localparam PAT_d     = 7'b0100001; // 'd' (Detected)
    localparam PAT_n     = 7'b0101011; // 'n' (None)
    localparam PAT_o     = 7'b0100011; // 'o' (Clear)
    localparam PAT_r     = 7'b0101111; // 'r' (Ready)
    localparam PAT_y     = 7'b0010001; // 'y'

    always @(*) begin
        case (digit_sel)
            // -----------------------------------------------------------------
            // Digit 0 (Rightmost Anode - Pin F2):
            // -----------------------------------------------------------------
            2'b00: begin
                digit_en = 4'b0001; // Enable Digit 0
                if (!processed)
                    Seven_Seg = PAT_BLANK;
                else if (detected)
                    Seven_Seg = PAT_0; // '0' of 100
                else
                    Seven_Seg = PAT_0; // '0' of 00
            end

            // -----------------------------------------------------------------
            // Digit 1 (Mid-Right Anode - Pin E1):
            // -----------------------------------------------------------------
            2'b01: begin
                digit_en = 4'b0010; // Enable Digit 1
                if (!processed)
                    Seven_Seg = PAT_y; // 'y' of rdy
                else if (detected)
                    Seven_Seg = PAT_0; // '0' of 100
                else
                    Seven_Seg = PAT_0; // '0' of 00
            end

            // -----------------------------------------------------------------
            // Digit 2 (Mid-Left Anode - Pin G5):
            // -----------------------------------------------------------------
            2'b10: begin
                digit_en = 4'b0100; // Enable Digit 2
                if (!processed)
                    Seven_Seg = PAT_d; // 'd' of rdy
                else if (detected)
                    Seven_Seg = PAT_1; // '1' of 100
                else
                    Seven_Seg = PAT_o; // 'o' of no
            end

            // -----------------------------------------------------------------
            // Digit 3 (Leftmost Anode - Pin G4):
            // -----------------------------------------------------------------
            2'b11: begin
                digit_en = 4'b1000; // Enable Digit 3
                if (!processed)
                    Seven_Seg = PAT_r; // 'r' of rdy
                else if (detected)
                    Seven_Seg = PAT_d; // 'd' for Detected!
                else
                    Seven_Seg = PAT_n; // 'n' for None!
            end

            default: begin
                digit_en  = 4'b0000;
                Seven_Seg = PAT_BLANK;
            end
        endcase
    end

endmodule
