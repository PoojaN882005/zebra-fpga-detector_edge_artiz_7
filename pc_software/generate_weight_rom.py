"""
generate_weight_rom.py
======================
Extracts real quantized weights and biases from `best (2).onnx` and formats them
into a synthesizable Verilog ROM module (`fpga_rtl/weight_rom.v`).
"""

import sys
from pathlib import Path
import numpy as np
import onnx
from onnx import numpy_helper

def main():
    onnx_path = Path(r"D:\Downloads\best (2).onnx")
    if not onnx_path.exists():
        print(f"[ERROR] Cannot find {onnx_path}")
        sys.exit(1)

    print(f"[INFO] Loading ONNX model from: {onnx_path}")
    model = onnx.load(str(onnx_path))
    weights = {init.name: numpy_helper.to_array(init) for init in model.graph.initializer}

    # Extract Conv0 (Stem Feature Extractor)
    w0 = weights['model.0.conv.weight']  # (32, 3, 3, 3)
    b0 = weights['model.0.conv.bias']    # (32,)

    scale_w0 = 127.0 / max(abs(w0.min()), abs(w0.max()))
    w0_q = np.clip(np.round(w0 * scale_w0), -128, 127).astype(np.int8).flatten()

    scale_b0 = 127.0 / max(abs(b0.min()), abs(b0.max()))
    b0_q = np.clip(np.round(b0 * scale_b0), -128, 127).astype(np.int8).flatten()

    # Extract Detection Head
    w_head = weights['model.22.cv3.0.2.weight']  # (1, 128, 1, 1)
    b_head = weights['model.22.cv3.0.2.bias']    # (1,)

    scale_wh = 127.0 / (max(abs(w_head.min()), abs(w_head.max())) + 1e-6)
    wh_q = np.clip(np.round(w_head * scale_wh), -128, 127).astype(np.int8).flatten()
    bh_val = int(round(float(b_head[0]) * 16.0)) # 4-bit fractional fixed-point

    # Generate synthesizable Verilog file
    out_path = Path(__file__).resolve().parent.parent / "fpga_rtl" / "weight_rom.v"
    print(f"[INFO] Writing synthesizable Verilog ROM to: {out_path}")

    with open(out_path, "w") as f:
        f.write("// =============================================================================\n")
        f.write("// Module: weight_rom.v\n")
        f.write("// Project: Real-Time FPGA Zebra Crossing Detection System (Artix-7 XC7A35T)\n")
        f.write("// Source: Extracted directly from trained model: D:\\Downloads\\best (2).onnx\n")
        f.write("// Format: 8-bit Signed Quantized Weights (INT8 Two's Complement)\n")
        f.write("// =============================================================================\n\n")
        f.write("`timescale 1ns / 1ps\n\n")
        f.write("module weight_rom (\n")
        f.write("    input  wire        clk,\n")
        f.write("    input  wire [9:0]  conv0_w_addr,  // 0 to 863\n")
        f.write("    output reg  signed [7:0] conv0_w_data,\n")
        f.write("    input  wire [4:0]  conv0_b_addr,  // 0 to 31\n")
        f.write("    output reg  signed [7:0] conv0_b_data,\n")
        f.write("    input  wire [6:0]  head_w_addr,   // 0 to 127\n")
        f.write("    output reg  signed [7:0] head_w_data,\n")
        f.write("    output wire signed [15:0] head_b_data\n")
        f.write(");\n\n")
        f.write(f"    assign head_b_data = 16'sh{bh_val & 0xFFFF:04X}; // Fixed-point bias = {float(b_head[0]):.4f}\n\n")

        # Conv0 Weights ROM
        f.write("    // -------------------------------------------------------------------------\n")
        f.write("    // Layer 0 Convolutional Weights (864 INT8 values)\n")
        f.write("    // -------------------------------------------------------------------------\n")
        f.write("    always @(posedge clk) begin\n")
        f.write("        case (conv0_w_addr)\n")
        for i, val in enumerate(w0_q):
            hex_val = int(val) & 0xFF
            f.write(f"            10'd{i:3d}: conv0_w_data <= 8'sh{hex_val:02X};\n")
        f.write("            default: conv0_w_data <= 8'sh00;\n")
        f.write("        endcase\n")
        f.write("    end\n\n")

        # Conv0 Bias ROM
        f.write("    // -------------------------------------------------------------------------\n")
        f.write("    // Layer 0 Convolutional Biases (32 INT8 values)\n")
        f.write("    // -------------------------------------------------------------------------\n")
        f.write("    always @(posedge clk) begin\n")
        f.write("        case (conv0_b_addr)\n")
        for i, val in enumerate(b0_q):
            hex_val = int(val) & 0xFF
            f.write(f"            5'd{i:2d}: conv0_b_data <= 8'sh{hex_val:02X};\n")
        f.write("            default: conv0_b_data <= 8'sh00;\n")
        f.write("        endcase\n")
        f.write("    end\n\n")

        # Head Weights ROM
        f.write("    // -------------------------------------------------------------------------\n")
        f.write("    // Detection Head Weights (128 INT8 values)\n")
        f.write("    // -------------------------------------------------------------------------\n")
        f.write("    always @(posedge clk) begin\n")
        f.write("        case (head_w_addr)\n")
        for i, val in enumerate(wh_q):
            hex_val = int(val) & 0xFF
            f.write(f"            7'd{i:3d}: head_w_data <= 8'sh{hex_val:02X};\n")
        f.write("            default: head_w_data <= 8'sh00;\n")
        f.write("        endcase\n")
        f.write("    end\n\n")

        f.write("endmodule\n")

    print("[SUCCESS] Synthesizable weight ROM successfully generated!")

if __name__ == "__main__":
    main()
