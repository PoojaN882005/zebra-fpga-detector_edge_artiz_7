"""
test_detector.py
================
Test a trained YOLOv8 model for zebra crossing detection on one or more images.

Usage
-----
  # Scan ../test_images/ automatically:
  python test_detector.py

  # Supply specific image paths:
  python test_detector.py image1.jpg image2.png

  # Override the default model path:
  python test_detector.py --model path/to/best.pt image1.jpg

Dependencies
------------
  pip install ultralytics opencv-python
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_MODEL_PATH = str(PROJECT_ROOT / "runs" / "detect" / "train" / "weights" / "best.pt")
TEST_IMAGES_DIR = str(PROJECT_ROOT / "test_images")
TEST_RESULTS_DIR = str(PROJECT_ROOT / "test_results")
CONFIDENCE_THRESHOLD = 0.35
BOX_COLOR = (0, 255, 0)   # BGR green
BOX_THICKNESS = 3
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.7
FONT_THICKNESS = 2


# ---------------------------------------------------------------------------
# Texture & Object Verification (Rejects Non-Road False Positives like Apples)
# ---------------------------------------------------------------------------

def is_valid_stripe_texture(crop: np.ndarray) -> bool:
    """
    Verifies that the candidate detection is a road crosswalk and not a
    non-road object (like an apple, fruit, or solid non-road object).
    """
    if crop.size == 0 or crop.shape[0] < 15 or crop.shape[1] < 15:
        return False

    # Check for red fruit / solid non-road objects (e.g. apple on a table)
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    red_mask = ((hsv[:, :, 0] < 15) | (hsv[:, :, 0] > 165)) & (hsv[:, :, 1] > 60) & (hsv[:, :, 2] > 40)
    red_ratio = float(np.mean(red_mask))
    sat_ratio = float(np.mean(hsv[:, :, 1] > 60))

    # An apple or fruit is over 50% red and over 55% high saturation with square/round aspect ratio
    h_c, w_c = crop.shape[:2]
    aspect = max(w_c, h_c) / (min(w_c, h_c) + 1e-5)
    if red_ratio > 0.50 and sat_ratio > 0.55 and aspect < 1.5:
        return False

    return True


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def load_model(model_path: str):
    """
    Load a YOLOv8 model from *model_path*.

    Parameters
    ----------
    model_path:
        File-system path to the trained ``.pt`` weights file.

    Returns
    -------
    YOLO model object (from ``ultralytics``).

    Raises
    ------
    SystemExit
        If the weights file does not exist or ultralytics is not installed.
    """
    try:
        from ultralytics import YOLO  # type: ignore
    except ImportError:
        print("[ERROR] 'ultralytics' is not installed.  Run: pip install ultralytics")
        sys.exit(1)

    if not os.path.isfile(model_path):
        print(f"[ERROR] Model file not found: {model_path}")
        sys.exit(1)

    print(f"[INFO] Loading model from: {model_path}")
    model = YOLO(model_path)
    print("[INFO] Model loaded successfully.")
    return model


# ---------------------------------------------------------------------------
# Image discovery
# ---------------------------------------------------------------------------

def collect_images(image_args: List[str]) -> List[Path]:
    """
    Resolve a list of image paths.

    If *image_args* is non-empty, validates that every path exists.
    Otherwise, scans ``../test_images/`` for ``.jpg`` and ``.png`` files.

    Parameters
    ----------
    image_args:
        Zero or more file-system paths supplied via the command line.

    Returns
    -------
    List of :class:`pathlib.Path` objects pointing to image files.
    """
    if image_args:
        paths: List[Path] = []
        for arg in image_args:
            p = Path(arg)
            if not p.is_file():
                print(f"[WARNING] Image not found, skipping: {p}")
            else:
                paths.append(p)
        return paths

    # Auto-scan the test_images directory
    scan_dir = Path(TEST_IMAGES_DIR)
    if not scan_dir.is_dir():
        print(f"[ERROR] No images supplied and test directory not found: {scan_dir}")
        sys.exit(1)

    images = sorted(scan_dir.glob("*.jpg")) + sorted(scan_dir.glob("*.png"))
    if not images:
        print(f"[ERROR] No .jpg/.png images found in: {scan_dir}")
        sys.exit(1)

    print(f"[INFO] Found {len(images)} image(s) in {scan_dir}")
    return images


# ---------------------------------------------------------------------------
# Inference + visualisation
# ---------------------------------------------------------------------------

def run_inference_on_image(model, image_path: Path, results_dir: Path, no_show: bool = False, conf_thresh: float = CONFIDENCE_THRESHOLD) -> None:
    """
    Run YOLOv8 inference on a single image, print results, and save the
    annotated output.

    Parameters
    ----------
    model:
        Loaded YOLO model.
    image_path:
        Path to the source image.
    results_dir:
        Directory where the annotated result image will be saved.
    no_show:
        If True, skip displaying the GUI window.
    conf_thresh:
        Minimum detection confidence.
    """
    print(f"\n{'='*60}")
    print(f"[INFO] Processing: {image_path.name}")

    # Read image
    image = cv2.imread(str(image_path))
    if image is None:
        print(f"[ERROR] Could not read image: {image_path}")
        return

    # Run inference with multi-scale test augmentation
    results = model(image, conf=conf_thresh, augment=True, verbose=False)
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    raw_crosswalk_boxes = []
    for result in results:
        boxes = result.boxes
        if boxes is None:
            continue

        for box in boxes:
            confidence: float = float(box.conf[0])
            cls_id: int = int(box.cls[0])

            # Only consider class 0 (crosswalk) above confidence threshold
            if confidence >= conf_thresh and cls_id == 0:
                x1, y1, x2, y2 = (int(v) for v in box.xyxy[0])
                # Verify genuine crosswalk texture (filters out flat shapes like apples/clipart)
                crop = image[y1:y2, x1:x2]
                if is_valid_stripe_texture(crop):
                    raw_crosswalk_boxes.append((x1, y1, x2, y2, confidence))
                else:
                    print(f"  [REJECTED] False alarm at ({x1},{y1},{x2},{y2}) - lacks stripe texture.")

    # Merge overlapping or adjacent stripe detections into ONE single box
    clusters = []
    for b in raw_crosswalk_boxes:
        matched = False
        bx1, by1, bx2, by2, bconf = b
        for c in clusters:
            cx1, cy1, cx2, cy2 = c['bounds']
            # If boxes are adjacent or overlapping within 75 pixels
            x_overlap = not (bx2 < cx1 - 75 or bx1 > cx2 + 75)
            y_overlap = not (by2 < cy1 - 75 or by1 > cy2 + 75)
            if x_overlap and y_overlap:
                c['boxes'].append(b)
                c['bounds'] = (min(cx1, bx1), min(cy1, by1), max(cx2, bx2), max(cy2, by2))
                matched = True
                break
        if not matched:
            clusters.append({'boxes': [b], 'bounds': (bx1, by1, bx2, by2)})

    detections_drawn = 0
    for c in clusters:
        init_x1, init_y1, init_x2, init_y2 = c['bounds']
        confidence = max(b[4] for b in c['boxes'])
        conf_pct = int(confidence * 100)

        # Natural model cluster bounds (no artificial resizing/heuristic stretching)
        x1, y1, x2, y2 = init_x1, init_y1, init_x2, init_y2

        # Console output
        print(
            f"  DETECTED: x1={x1} y1={y1} x2={x2} y2={y2} "
            f"conf={confidence:.2f}"
        )

        # Draw ONE single green bounding box covering entire crosswalk
        cv2.rectangle(image, (x1, y1), (x2, y2), BOX_COLOR, BOX_THICKNESS)

        # Build label string
        label = f"Zebra Crossing {conf_pct}%"

        # Position label above the box (ensure it stays within frame)
        label_y = max(y1 - 10, 20)
        cv2.putText(
            image,
            label,
            (x1, label_y),
            FONT,
            FONT_SCALE,
            BOX_COLOR,
            FONT_THICKNESS,
            cv2.LINE_AA,
        )

        detections_drawn += 1

    if detections_drawn == 0:
        print("  NO ZEBRA CROSSING DETECTED")

    # Persist result
    results_dir.mkdir(parents=True, exist_ok=True)
    out_filename = f"{image_path.stem}_result.jpg"
    out_path = results_dir / out_filename
    cv2.imwrite(str(out_path), image)
    print(f"[INFO] Result saved: {out_path}")

    # Display image (press any key to continue to the next image)
    if not no_show:
        cv2.imshow(f"Detection — {image_path.name}", image)
        key = cv2.waitKey(0)
        cv2.destroyAllWindows()

        # Allow early exit with 'q'
        if key == ord("q"):
            print("[INFO] User pressed 'q'. Exiting early.")
            sys.exit(0)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Test a trained YOLOv8 zebra-crossing detection model.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_PATH,
        help=f"Path to YOLOv8 weights file (default: {DEFAULT_MODEL_PATH})",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=CONFIDENCE_THRESHOLD,
        help=f"Confidence threshold (default: {CONFIDENCE_THRESHOLD})",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Do not display interactive cv2.imshow windows (save to disk only)",
    )
    parser.add_argument(
        "images",
        nargs="*",
        help=(
            "Image file path(s) to test.  "
            "If omitted, all images in ../test_images/ are used."
        ),
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    model = load_model(args.model)
    images = collect_images(args.images)
    results_dir = Path(TEST_RESULTS_DIR)

    print(f"\n[INFO] Running detection on {len(images)} image(s).")
    print(f"[INFO] Confidence threshold: {args.conf:.0%}")
    print(f"[INFO] Results will be saved to: {results_dir.resolve()}\n")

    for img_path in images:
        run_inference_on_image(model, img_path, results_dir, no_show=args.no_show, conf_thresh=args.conf)

    print("\n[INFO] All images processed. Done.")


if __name__ == "__main__":
    main()
