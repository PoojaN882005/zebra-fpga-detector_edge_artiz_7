# Zebra Crossing Detection System — Edge Artix-7 FPGA
**A Hybrid Classical + Neural Network Approach for Real-Time Pedestrian Crosswalk Detection**

---

## Project Structure
```
zebra-fpga-detector/
├── colab_training/
│   └── zebra_train_colab.ipynb    ← Upload to Google Colab first!
├── pc_software/
│   ├── test_detector.py           ← Test model on local images
│   ├── fpga_interface.py          ← PC<->FPGA UART communication
│   ├── dataset_downloader.py      ← Dataset download helper
│   └── zebra_test_images.py       ← Download test images
├── fpga_rtl/
│   ├── zebra_top.v                ← Top-level Verilog module
│   ├── zebra_detector.v           ← Classical detection engine
│   └── edge_artix7_zebra.xdc     ← Pin constraints (XDC)
├── dataset/                       ← Put your downloaded dataset here
├── test_images/                   ← Test images go here
└── README.md
```

---

## Quick Start (Follow This Order!)

### STEP 1 — Get the Dataset (15 min)
1. Go to: https://universe.roboflow.com/search?q=zebra+crossing
2. Sign up (free) and find a dataset with 500+ images
3. Download in **YOLOv8 format**
4. Extract to `dataset/` folder so you have `dataset/data.yaml`

### STEP 2 — Train on Google Colab (1-2 hours, free GPU!)
1. Go to https://colab.research.google.com
2. Upload `colab_training/zebra_train_colab.ipynb`
3. Runtime → Change runtime type → **T4 GPU**
4. Fill in your Roboflow API key in Cell 2
5. Run all cells — training takes ~1 hour with 200 epochs
6. Download `zebra_best.pt` when done
7. Place it at: `runs/detect/train/weights/best.pt`

### STEP 3 — Test on PC (5 min)
```bash
# Put some zebra crossing images in test_images/ folder, then:
cd pc_software
python test_detector.py --model ../runs/detect/train/weights/best.pt
```

### STEP 4 — FPGA Integration (After Stage 1 approval)
1. Open Vivado → Create New Project → Artix-7 XC7A35T-1FTG256C
2. Add all files from `fpga_rtl/` as source files
3. Add `edge_artix7_zebra.xdc` as constraints
4. Run Synthesis → Implementation → Generate Bitstream
5. Program the board

### STEP 5 — PC<->FPGA Communication
```bash
cd pc_software
# Find your UART port first (check Device Manager for "USB Serial Port")
python fpga_interface.py --port COM3 --image ../test_images/zebra1.jpg
```

---

## Hardware Connections (for Stage 2+)

| Signal | FPGA Pin | Notes |
|--------|----------|-------|
| USB-UART RX | A18 | Connected to FTDI chip on board |
| USB-UART TX | B18 | Connected to FTDI chip on board |
| LED0 (Blue) | U16 | Receiving image indicator |
| LED1 (Yellow) | E19 | Processing indicator |
| LED2 (Green) | U19 | Zebra DETECTED |
| LED3 (Red) | V19 | NOT detected / error |

---

## Communication Protocol

### PC → FPGA (Send Image):
```
Byte 0:     0xAA  (sync byte 1)
Byte 1:     0xBB  (sync byte 2)
Byte 2:     Width[15:8]   (e.g., 0x01 for 320)
Byte 3:     Width[7:0]    (e.g., 0x40 for 320)
Byte 4:     Height[15:8]  (e.g., 0x00 for 240)
Byte 5:     Height[7:0]   (e.g., 0xF0 for 240)
Bytes 6+:   RGB565 pixel data, MSB first, row by row
            Total = Width × Height × 2 bytes
```

### FPGA → PC (Result):
```
Byte 0:     0x01 = Detected, 0x00 = Not Detected
If detected (Byte 0 = 0x01):
Byte 1-2:   X1 (16-bit, MSB first)
Byte 3-4:   Y1 (16-bit, MSB first)
Byte 5-6:   X2 (16-bit, MSB first)
Byte 7-8:   Y2 (16-bit, MSB first)
```

---

## FPGA Resources Used (Estimated for XC7A35T)

| Resource | Used | Available | % |
|----------|------|-----------|---|
| LUTs | ~5,000 | 20,800 | 24% |
| FFs | ~3,000 | 41,600 | 7% |
| BRAM (18Kb) | ~10 | 100 | 10% |
| DSP48 | ~4 | 90 | 4% |
| SDRAM | 32 MB | 32 MB | 100% |

---

## IEEE Paper Draft Notes

**Proposed Title:** "Real-Time Zebra Crossing Detection on a Resource-Constrained Artix-7 FPGA Using a Hybrid Classical-Neural Architecture"

**Key Contributions (for paper):**
1. Novel hybrid approach: Classical stripe detection + YOLO-trained feature validation
2. Ultra-low resource usage (fits in XC7A35T with 90 DSPs)
3. Complete PC↔FPGA pipeline with UART-based image transfer
4. 320×240 processing at potential 30+ FPS with pipelined design
5. Validated against Roboflow dataset, tested on unseen images

**Recommended venues:**
- IEEE Access (open access, fast review)
- IEEE Transactions on Intelligent Transportation Systems
- ISCAS 2025/2026 (conference)
- ISVLSI 2025/2026 (conference)

---

## Troubleshooting

**Model not detecting anything:**
- Make sure `best.pt` path is correct
- Try lowering confidence threshold: `--conf 0.2`
- Retrain with more epochs or more data

**FPGA not responding:**
- Check COM port in Device Manager
- Verify baud rate is 115200 on both sides
- Check LED0 (blue) — should light up when receiving

**SDRAM not working:**
- Verify XDC pin assignments match your exact board revision
- Check the board schematic PDF from allaboutfpga.com
