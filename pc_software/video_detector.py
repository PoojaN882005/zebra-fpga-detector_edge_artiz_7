"""
video_detector.py
=================
Real-time Zebra Crossing Detection on Video Streams / Webcams.
Supports:
  - Video files (.mp4, .avi, .mkv)
  - Live webcam / camera input (device 0, 1)
  - Frame-by-frame green bounding box rendering
  - Video output recording

Usage:
------
  # Detect on video file:
  python video_detector.py --source path/to/video.mp4

  # Detect on live webcam:
  python video_detector.py --source 0

  # Save annotated output video:
  python video_detector.py --source path/to/video.mp4 --save
"""

import argparse
import sys
import time
from pathlib import Path
import cv2
import numpy as np
from ultralytics import YOLO

BOX_COLOR = (0, 255, 0)      # BGR bright green
BOX_THICKNESS = 3
FONT = cv2.FONT_HERSHEY_SIMPLEX

def is_valid_stripe_texture(crop: np.ndarray) -> bool:
    """Verifies candidate region has stripe edges, strictly rejecting fruits, cloth, and non-roads."""
    if crop.size == 0 or crop.shape[0] < 15 or crop.shape[1] < 15:
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    red_mask = ((h < 15) | (h > 165)) & (s > 75) & (v > 45)
    if np.mean(red_mask) > 0.18:
        return False

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    h_prof = np.mean(thresh, axis=0) > 120
    v_prof = np.mean(thresh, axis=1) > 120
    h_trans = np.sum(np.diff(h_prof.astype(int)) != 0)
    v_trans = np.sum(np.diff(v_prof.astype(int)) != 0)
    return bool(max(h_trans, v_trans) >= 2)

def expand_box_to_adjacent_stripes(image: np.ndarray, box: tuple) -> tuple:
    x1, y1, x2, y2 = box
    h_img, w_img = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    box_h = y2 - y1
    box_w = x2 - x1
    if box_w > 2.0 * box_h:
        pad_x1 = max(0, x1 - 20)
        pad_x2 = min(w_img, x2 + 20)
        strip_region = gray[:, pad_x1:pad_x2]
        row_diffs = np.std(strip_region, axis=1)
        seed_std = np.median(row_diffs[y1:y2])
        if seed_std > 20.0:
            std_thresh = max(18.0, seed_std * 0.45)
            new_y2 = y2
            while new_y2 < h_img - 5 and row_diffs[new_y2] > std_thresh and (new_y2 - y2) < int(h_img * 0.4):
                new_y2 += 4
            new_y1 = y1
            while new_y1 > 10 and row_diffs[new_y1] > std_thresh and (y1 - new_y1) < int(h_img * 0.3):
                new_y1 -= 4
            return (x1, new_y1, x2, new_y2)
    return box

def run_video_detection(model_path: str, source: str, conf_thresh: float = 0.35, save_out: bool = False):
    print(f"[INFO] Loading model from: {model_path}")
    model = YOLO(model_path)

    # Open video source (int for webcam, string for file)
    src = int(source) if source.isdigit() else source
    cap = cv2.VideoCapture(src)

    if not cap.isOpened():
        print(f"[ERROR] Could not open video source: {source}")
        sys.exit(1)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    print(f"[INFO] Video stream: {width}x{height} @ {fps:.1f} FPS")

    writer = None
    if save_out and not source.isdigit():
        out_name = f"result_{Path(source).stem}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(out_name, fourcc, fps, (width, height))
        print(f"[INFO] Saving output to: {out_name}")

    prev_time = time.time()
    frame_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            # YOLO inference
            results = model.predict(frame, conf=conf_thresh, verbose=False)[0]
            boxes = results.boxes
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Collect all crosswalk boxes
            raw_crosswalk_boxes = []
            if len(boxes) > 0:
                for b in boxes:
                    cls_id = int(b.cls[0].item())
                    conf = float(b.conf[0].item())
                    if cls_id == 0 and conf >= conf_thresh:
                        x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
                        crop = frame[y1:y2, x1:x2]
                        if is_valid_stripe_texture(crop):
                            raw_crosswalk_boxes.append((x1, y1, x2, y2, conf))

            # Merge adjacent stripes into one single box
            clusters = []
            for b in raw_crosswalk_boxes:
                matched = False
                bx1, by1, bx2, by2, bconf = b
                for c in clusters:
                    cx1, cy1, cx2, cy2 = c['bounds']
                    if not (bx2 < cx1 - 75 or bx1 > cx2 + 75) and not (by2 < cy1 - 75 or by1 > cy2 + 75):
                        c['boxes'].append(b)
                        c['bounds'] = (min(cx1, bx1), min(cy1, by1), max(cx2, bx2), max(cy2, by2))
                        matched = True
                        break
                if not matched:
                    clusters.append({'boxes': [b], 'bounds': (bx1, by1, bx2, by2)})

            zebra_found = len(clusters) > 0
            for c in clusters:
                init_x1, init_y1, init_x2, init_y2 = c['bounds']
                conf = max(b[4] for b in c['boxes'])
                # Expand box to cover all connected parallel stripes
                x1, y1, x2, y2 = expand_box_to_adjacent_stripes(frame, (init_x1, init_y1, init_x2, init_y2))
                # Draw single green box
                cv2.rectangle(frame, (x1, y1), (x2, y2), BOX_COLOR, BOX_THICKNESS)
                label = f"Zebra Crossing {conf*100:.0f}%"
                cv2.putText(frame, label, (x1, max(25, y1 - 10)), FONT, 0.7, BOX_COLOR, 2)

            # Measure FPS
            curr_time = time.time()
            current_fps = 1.0 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 30.0
            prev_time = curr_time

            # Status HUD
            status_text = "STATUS: ZEBRA DETECTED" if zebra_found else "STATUS: SCANNING..."
            hud_color = (0, 255, 0) if zebra_found else (0, 180, 255)
            cv2.putText(frame, status_text, (20, 35), FONT, 0.8, hud_color, 2)
            cv2.putText(frame, f"FPS: {current_fps:.1f}", (20, 70), FONT, 0.7, (255, 255, 255), 2)

            if writer:
                writer.write(frame)

            cv2.imshow("Real-Time Zebra Crossing Detection", frame)
            key = cv2.waitKey(1)
            if key == ord('q') or key == 27:
                print("[INFO] User stopped playback.")
                break

    finally:
        cap.release()
        if writer:
            writer.release()
        cv2.destroyAllWindows()
        print(f"[INFO] Processed {frame_count} frames. Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real-time Zebra Crossing Detection on Video")
    parser.add_argument("--source", default="0", help="Video file path or webcam index (default: 0)")
    parser.add_argument("--model", default="../runs/detect/train/weights/best.pt", help="Path to weights")
    parser.add_argument("--conf", type=float, default=0.65, help="Confidence threshold")
    parser.add_argument("--save", action="store_true", help="Save annotated output video")
    args = parser.parse_args()

    run_video_detection(args.model, args.source, args.conf, args.save)
