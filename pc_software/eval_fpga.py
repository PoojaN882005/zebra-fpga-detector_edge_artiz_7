import sys, os
from pathlib import Path
import cv2, numpy as np

sys.path.append(str(Path(__file__).resolve().parent))
from fpga_sim import simulate_fpga_pipeline

test_dir = Path(__file__).resolve().parent.parent / "test_images"
out_dir = Path(__file__).resolve().parent.parent / "test_results" / "fpga_eval"
out_dir.mkdir(parents=True, exist_ok=True)

test_imgs = [
    ("woman_crossing.jpg", True),
    ("weathered_crosswalk.jpg", True),
    ("green_night_crosswalk.jpg", True),
    ("user_cctv_crosswalk.jpg", True),
    ("user_london_street.jpg", True),
    ("user_residential_street.jpg", True),
    ("Screenshot 2026-10-20 220029.png", True),
    ("bus_negative.jpg", False)
]

# Check if apple.jpg exists or use apple_clean_result
apple_path = test_dir / "apple.jpg"
if not apple_path.exists():
    apple_path = Path(__file__).resolve().parent.parent / "test_results" / "apple_result.jpg"
if apple_path.exists():
    test_imgs.append((apple_path.name, False))

print("=" * 85)
print("%-32s | %-12s | %-14s | %-7s | %-10s | %-6s" % ("IMAGE", "GROUND TRUTH", "FPGA RESULT", "STRIPES", "LATENCY", "STATUS"))
print("-" * 85)

correct = 0
total = 0

for name, is_zebra in test_imgs:
    p = test_dir / name
    if not p.exists():
        p = Path(__file__).resolve().parent.parent / "test_results" / name
    if not p.exists():
        continue
    res = simulate_fpga_pipeline(str(p))
    if res is None:
        continue
        
    total += 1
    det = res["detected"]
    is_correct = (det == is_zebra)
    if is_correct:
        correct += 1
        
    gt_str = "ZEBRA" if is_zebra else "NON-ZEBRA"
    fpga_str = "DETECTED" if det else "NO ZEBRA"
    status_str = "PASS" if is_correct else "FAIL"
    
    print("%-32s | %-12s | %-14s | %-7d | %6.2f ms  | %-6s" % (name[:32], gt_str, fpga_str, res["stripe_count"], res["latency_ms"], status_str))
    
    # Save visualized result
    vis = res["resized"].copy()
    if det:
        x1, y1, x2, y2 = res["bbox"]
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(vis, "FPGA: %d stripes" % res["stripe_count"], (x1, max(y1 - 6, 12)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
    cv2.imwrite(str(out_dir / ("fpga_%s.jpg" % Path(name).stem)), vis)

print("-" * 85)
if total > 0:
    print("OVERALL HARDWARE ACCURACY: %d/%d (%.1f%%)" % (correct, total, (correct/total)*100.0))
print("Visualizations saved to: %s" % out_dir)
print("=" * 85)
