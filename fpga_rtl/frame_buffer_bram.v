// =============================================================================
// Module: frame_buffer_bram.v
// Project: Real-Time FPGA Zebra Crossing Detection System
// Target: Xilinx Artix-7 XC7A35T-1FTG256C
//
// Description:
//   Dual-Port Synchronous Block RAM for storing a 320x240 8-bit grayscale frame.
//   Total memory: 320 x 240 = 76,800 bytes (614.4 Kbits).
//   Utilizes ~17 RAMB36E1 primitives (~34% of Artix-7 XC7A35T Block RAM).
//
// Ports:
//   Port A: Write-only port (used by UART/Camera receiver to stream in pixels)
//   Port B: Read-only port (used by Detection Engine to read raster scan data)
// =============================================================================

`timescale 1ns / 1ps

module frame_buffer_bram #(
    parameter DATA_WIDTH = 8,
    parameter ADDR_WIDTH = 17,       // 2^17 = 131,072 > 76,800
    parameter FRAME_SIZE = 76800     // 320 * 240
)(
    input  wire                  clk,
    
    // Port A (Write Interface)
    input  wire                  we_a,
    input  wire [ADDR_WIDTH-1:0] addr_a,
    input  wire [DATA_WIDTH-1:0] din_a,
    
    // Port B (Read Interface)
    input  wire                  en_b,
    input  wire [ADDR_WIDTH-1:0] addr_b,
    output reg  [DATA_WIDTH-1:0] dout_b
);

    // Synthesis attribute directing Vivado to infer dedicated Block RAM
    (* ram_style = "block" *) reg [DATA_WIDTH-1:0] ram [0:FRAME_SIZE-1];

    // Port A: Synchronous Write
    always @(posedge clk) begin
        if (we_a) begin
            if (addr_a < FRAME_SIZE)
                ram[addr_a] <= din_a;
        end
    end

    // Port B: Synchronous Read (1-cycle latency)
    always @(posedge clk) begin
        if (en_b) begin
            if (addr_b < FRAME_SIZE)
                dout_b <= ram[addr_b];
            else
                dout_b <= {DATA_WIDTH{1'b0}};
        end
    end

endmodule
