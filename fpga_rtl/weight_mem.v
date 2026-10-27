// =============================================================================
// Module: weight_mem.v
// Project: Real-Time FPGA Zebra Crossing Detection System
// Target: Xilinx Artix-7 XC7A35T
// Description:
//   Synchronous Block RAM with initialization from hardware .mem hex files.
// =============================================================================

`timescale 1ns / 1ps

module weight_mem #(
    parameter DATA_WIDTH = 16,
    parameter DEPTH      = 49152,
    parameter ADDR_WIDTH = 16,
    parameter MEM_FILE   = "w1.mem"
)(
    input  wire                  clk,
    input  wire [ADDR_WIDTH-1:0] addr,
    output reg  signed [DATA_WIDTH-1:0] data_out
);

    (* ram_style = "block" *) reg signed [DATA_WIDTH-1:0] mem [0:DEPTH-1];

    initial begin
        $readmemh(MEM_FILE, mem);
    end

    always @(posedge clk) begin
        data_out <= mem[addr];
    end

endmodule
