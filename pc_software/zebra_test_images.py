"""
zebra_test_images.py
====================
Download random zebra crossing images from Google for testing
the trained YOLOv8 model on unseen data.

Usage:
    python zebra_test_images.py          # Download test images
    python zebra_test_images.py --test   # Also run model on them
"""

import os
import sys
import urllib.request
import urllib.parse
import time
import argparse
from pathlib import Path

# Test images: mix of zebra crossings AND non-zebra scenes (to test false positive rejection)
TEST_IMAGES = {
    # [OK] ZEBRA CROSSINGS (should be detected)
    "zebra_uk_1.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cc/Zebra_crossing.jpg/640px-Zebra_crossing.jpg",
    "zebra_aerial_1.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Pedestrian_crossing_-_geograph.org.uk_-_978750.jpg/640px-Pedestrian_crossing_-_geograph.org.uk_-_978750.jpg",
    # [NO] NON-ZEBRA (should NOT be detected — testing false positive rejection)
    "road_no_zebra.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a6/Road_in_Norway.jpg/640px-Road_in_Norway.jpg",
    "parking_lot.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/Parking_lot_in_Taipei.jpg/640px-Parking_lot_in_Taipei.jpg",
}

def download_test_images(output_dir: str = "../test_images") -> dict:
    """Download test images for model validation."""
    out_path = Path(output_dir)
    out_path.mkdir(exist_ok=True, parents=True)
    
    downloaded = {}
    
    print("=" * 60)
    print("[INFO] Downloading test images...")
    print("=" * 60)
    
    for filename, url in TEST_IMAGES.items():
        dest = out_path / filename
        is_zebra = "zebra" in filename or "crossing" in filename
        label = "[OK] ZEBRA (should detect)" if is_zebra else "[NO] NOT ZEBRA (should not detect)"
        
        print(f"\n{label}")
        print(f"  File: {filename}")
        
        if dest.exists():
            print(f"  Already exists, skipping.")
            downloaded[str(dest)] = is_zebra
            continue
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            
            with open(dest, 'wb') as f:
                f.write(data)
            
            print(f"  Downloaded ({len(data)//1024} KB)")
            downloaded[str(dest)] = is_zebra
        except Exception as e:
            print(f"  [WARN] Failed: {e}")
    
    print(f"\n[OK] Downloaded {len(downloaded)} images to {out_path.absolute()}")
    return downloaded


def run_model_test(downloaded: dict, model_path: str = "../runs/detect/train/weights/best.pt"):
    """Run the trained model on downloaded images and report results."""
    try:
        from ultralytics import YOLO
        import cv2
    except ImportError:
        print("ultralytics or opencv-python not installed.")
        return
    
    if not Path(model_path).exists():
        print(f"\n[WARN] Model not found at {model_path}")
        print("   Please train the model first using the Colab notebook.")
        print("   Then download best.pt and place it at the path above.")
        return
    
    model = YOLO(model_path)
    
    results_dir = Path("../test_results")
    results_dir.mkdir(exist_ok=True, parents=True)
    
    print("\n" + "=" * 60)
    print("[DETECT] Running zebra crossing detection on test images...")
    print("=" * 60)
    
    correct = 0
    total = len(downloaded)
    
    for img_path, is_zebra_gt in downloaded.items():
        if not Path(img_path).exists():
            continue
        
        img = cv2.imread(img_path)
        if img is None:
            print(f"  Could not read {img_path}")
            continue
        
        results = model(img_path, conf=0.3, verbose=False)
        
        boxes = results[0].boxes
        detected = len(boxes) > 0
        
        # Determine correctness
        if detected == is_zebra_gt:
            status = "[OK] CORRECT"
            correct += 1
        elif detected and not is_zebra_gt:
            status = "[NO] FALSE POSITIVE (drew box on non-zebra!)"
        else:
            status = "[WARN] FALSE NEGATIVE (missed zebra crossing)"
        
        expected = "Zebra" if is_zebra_gt else "Not Zebra"
        got = "Detected" if detected else "Not Detected"
        
        print(f"\n[{Path(img_path).name}]")
        print(f"  Expected: {expected}  |  Got: {got}  |  {status}")
        
        if detected:
            for box in boxes:
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                conf = box.conf[0].item()
                print(f"  Bounding Box: x1={x1}, y1={y1}, x2={x2}, y2={y2}, conf={conf:.3f}")
                # Draw green rectangle
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
                label = f"Zebra Crossing {conf*100:.0f}%"
                cv2.putText(img, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        else:
            cv2.putText(img, "No zebra crossing", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        
        # Save result
        out_file = results_dir / f"result_{Path(img_path).name}"
        cv2.imwrite(str(out_file), img)
        print(f"  Saved: {out_file}")
    
    print("\n" + "=" * 60)
    print(f"[STATS] RESULTS: {correct}/{total} correct ({100*correct/total:.1f}% accuracy)")
    print("=" * 60)
    print(f"\nResult images saved in: {results_dir.absolute()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test zebra crossing detector on random images")
    parser.add_argument("--test", action="store_true", help="Run model test after downloading")
    parser.add_argument("--model", default="../runs/detect/train/weights/best.pt", help="Path to trained model")
    parser.add_argument("--outdir", default="../test_images", help="Image download directory")
    args = parser.parse_args()
    
    downloaded = download_test_images(args.outdir)
    
    if args.test:
        run_model_test(downloaded, args.model)
    else:
        print("\n[TIP] Tip: Run with --test flag to also test the model:")
        print(f"   python {Path(__file__).name} --test")
        print("\nNext step: Train model using the Colab notebook, then test here.")
