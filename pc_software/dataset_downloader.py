"""
dataset_downloader.py
=====================
Helper script for obtaining and preparing the zebra-crossing dataset.

This script:
  1. Guides you through downloading a dataset from Roboflow Universe.
  2. Verifies the expected dataset directory structure.
  3. Shows basic dataset statistics (image counts, class names).
  4. Optionally augments existing images to expand the training set.

Usage
-----
  python dataset_downloader.py           # print instructions + open browser
  python dataset_downloader.py --verify  # check dataset structure
  python dataset_downloader.py --stats   # show image/class counts
  python dataset_downloader.py --augment # augment images in the dataset

Dependencies (core):
  pip install opencv-python pyyaml

Optional (for richer augmentation):
  pip install albumentations
"""

import argparse
import os
import sys
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Dataset layout expected by YOLOv8
# ---------------------------------------------------------------------------
DATASET_ROOT = Path("../dataset")
REQUIRED_DIRS = [
    "images/train",
    "images/val",
    "labels/train",
    "labels/val",
]
DATA_YAML = DATASET_ROOT / "data.yaml"

ROBOFLOW_URL = "https://universe.roboflow.com/search?q=zebra+crossing"
GITHUB_REPO  = "https://github.com/xN1ckuz/Crosswalks-Detection-using-YOLO"

AUGMENTED_SUFFIX = "_aug"  # appended to augmented image filenames


# ---------------------------------------------------------------------------
# Step-by-step download instructions
# ---------------------------------------------------------------------------

def print_download_instructions() -> None:
    """Print clear, numbered instructions for obtaining the dataset."""
    border = "=" * 70

    print(border)
    print("  ZEBRA CROSSING DATASET — DOWNLOAD INSTRUCTIONS")
    print(border)

    print("""
OPTION A: Roboflow Universe  (recommended — pre-labelled, YOLO format)
───────────────────────────────────────────────────────────────────────
  1. Open the URL below in your browser (this script will try to open it
     automatically):

       https://universe.roboflow.com/search?q=zebra+crossing

  2. Find a dataset that suits your project (e.g. "Crosswalk Detection",
     "Zebra Crossing Detection", etc.).

  3. Click on the dataset → click "Download Dataset".

  4. Choose Export Format: "YOLOv8"  (or "YOLOv5 PyTorch" — both work).

  5. Select "download zip to computer" when prompted.

  6. Extract the zip into the project dataset directory:

       ../dataset/

     The result should look like this:
       dataset/
       ├── images/
       │   ├── train/   ← training images (.jpg / .png)
       │   └── val/     ← validation images
       ├── labels/
       │   ├── train/   ← YOLO .txt annotations
       │   └── val/
       └── data.yaml    ← class names + paths config

  7. Verify with:  python dataset_downloader.py --verify
""")

    print("""
OPTION B: GitHub repository  (manual clone)
───────────────────────────────────────────────────────────────────────
  A curated crosswalk dataset is also available at:

    https://github.com/xN1ckuz/Crosswalks-Detection-using-YOLO

  Clone it and move the data into ../dataset/:

    git clone https://github.com/xN1ckuz/Crosswalks-Detection-using-YOLO
    # Then copy / reorganise images and labels into the expected layout.
""")

    print("""
OPTION C: Build your own dataset
───────────────────────────────────────────────────────────────────────
  1. Collect images containing zebra crossings (street view, dashcam, etc.).
  2. Annotate them with LabelImg or Roboflow Annotate (free tier).
  3. Export in YOLOv8 format and place in ../dataset/ as above.
""")

    print(border)


def open_roboflow_browser() -> None:
    """Attempt to open the Roboflow search URL in the default web browser."""
    print(f"\n[INFO] Attempting to open browser at:\n  {ROBOFLOW_URL}\n")
    try:
        opened = webbrowser.open(ROBOFLOW_URL)
        if opened:
            print("[INFO] Browser opened successfully.")
        else:
            print("[WARNING] Could not open browser automatically.")
            print(f"[INFO] Please navigate to:  {ROBOFLOW_URL}")
    except Exception as exc:
        print(f"[WARNING] Browser open failed ({exc}).")
        print(f"[INFO] Please navigate to:  {ROBOFLOW_URL}")


# ---------------------------------------------------------------------------
# Dataset structure verification
# ---------------------------------------------------------------------------

def verify_dataset_structure(dataset_root: Path = DATASET_ROOT) -> bool:
    """
    Check that the dataset directory contains all required sub-directories
    and a ``data.yaml`` configuration file.

    Parameters
    ----------
    dataset_root:
        Root directory of the dataset.

    Returns
    -------
    ``True`` if all required paths exist, ``False`` otherwise.
    """
    print(f"\n[INFO] Verifying dataset structure in: {dataset_root.resolve()}")
    all_ok = True

    # Check required sub-directories
    for rel_dir in REQUIRED_DIRS:
        full_path = dataset_root / rel_dir
        if full_path.is_dir():
            print(f"  [OK]      {rel_dir}/")
        else:
            print(f"  [MISSING] {rel_dir}/   ← directory not found")
            all_ok = False

    # Check data.yaml
    yaml_path = dataset_root / "data.yaml"
    if yaml_path.is_file():
        print(f"  [OK]      data.yaml")
    else:
        print(f"  [MISSING] data.yaml   ← YOLOv8 config file not found")
        all_ok = False

    if all_ok:
        print("\n[SUCCESS] Dataset structure looks correct!")
    else:
        print("\n[WARN] Dataset structure is incomplete.")
        print("       Run without flags for download instructions.")

    return all_ok


# ---------------------------------------------------------------------------
# Dataset statistics
# ---------------------------------------------------------------------------

def _count_images(directory: Path) -> int:
    """Return the number of .jpg and .png files in *directory*."""
    if not directory.is_dir():
        return 0
    return (
        len(list(directory.glob("*.jpg")))
        + len(list(directory.glob("*.png")))
        + len(list(directory.glob("*.jpeg")))
    )


def _read_class_names(yaml_path: Path) -> List[str]:
    """
    Parse class names from ``data.yaml``.

    Returns an empty list if the file is missing or malformed.
    """
    if not yaml_path.is_file():
        return []
    try:
        import yaml  # type: ignore  (pyyaml)
        with yaml_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        names = data.get("names", [])
        # names may be a list or a dict {0: 'class', …}
        if isinstance(names, dict):
            names = [names[k] for k in sorted(names)]
        return names
    except Exception as exc:
        print(f"[WARNING] Could not parse data.yaml: {exc}")
        return []


def show_dataset_stats(dataset_root: Path = DATASET_ROOT) -> None:
    """
    Print a summary of image counts and class names found in the dataset.

    Parameters
    ----------
    dataset_root:
        Root directory of the dataset.
    """
    print(f"\n[INFO] Dataset statistics for: {dataset_root.resolve()}")
    print("-" * 50)

    for split in ("train", "val", "test"):
        img_dir = dataset_root / "images" / split
        n = _count_images(img_dir)
        if n or img_dir.is_dir():
            print(f"  {split:6s} images : {n:>5d}")

    class_names = _read_class_names(dataset_root / "data.yaml")
    if class_names:
        print(f"\n  Classes ({len(class_names)}):")
        for idx, name in enumerate(class_names):
            print(f"    {idx}: {name}")
    else:
        print("\n  Classes: (data.yaml not found or unreadable)")

    print("-" * 50)


# ---------------------------------------------------------------------------
# Augmentation
# ---------------------------------------------------------------------------

def _augment_with_albumentations(
    images_dir: Path,
    labels_dir: Path,
    output_images_dir: Path,
    output_labels_dir: Path,
    num_augmentations: int = 2,
) -> int:
    """
    Augment images using the `albumentations` library.

    Applies horizontal flip, brightness/contrast shift, rotation, and blur.

    Parameters
    ----------
    images_dir, labels_dir:
        Source image and YOLO-label directories.
    output_images_dir, output_labels_dir:
        Destination directories for augmented files.
    num_augmentations:
        How many augmented copies to produce per source image.

    Returns
    -------
    Number of augmented images successfully written.
    """
    import albumentations as A  # type: ignore

    transform = A.Compose(
        [
            A.HorizontalFlip(p=0.5),
            A.RandomBrightnessContrast(p=0.5),
            A.Rotate(limit=10, p=0.5),
            A.GaussianBlur(blur_limit=(3, 5), p=0.3),
        ],
        bbox_params=A.BboxParams(format="yolo", label_fields=["class_labels"]),
    )

    import cv2  # local import to keep top-level dependencies minimal

    output_images_dir.mkdir(parents=True, exist_ok=True)
    output_labels_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    image_files = (
        list(images_dir.glob("*.jpg"))
        + list(images_dir.glob("*.jpeg"))
        + list(images_dir.glob("*.png"))
    )

    for img_path in image_files:
        label_path = labels_dir / (img_path.stem + ".txt")
        image = cv2.imread(str(img_path))
        if image is None:
            continue

        # Parse YOLO labels: class cx cy w h (normalised)
        bboxes: List[List[float]] = []
        class_labels: List[int] = []
        if label_path.is_file():
            for line in label_path.read_text().strip().splitlines():
                parts = line.split()
                if len(parts) == 5:
                    cls, cx, cy, bw, bh = int(parts[0]), *map(float, parts[1:])
                    bboxes.append([cx, cy, bw, bh])
                    class_labels.append(cls)

        for i in range(num_augmentations):
            augmented = transform(
                image=image,
                bboxes=bboxes,
                class_labels=class_labels,
            )
            aug_img = augmented["image"]
            aug_boxes = augmented["bboxes"]
            aug_labels = augmented["class_labels"]

            stem = f"{img_path.stem}{AUGMENTED_SUFFIX}{i}"
            out_img_path = output_images_dir / f"{stem}.jpg"
            out_lbl_path = output_labels_dir / f"{stem}.txt"

            cv2.imwrite(str(out_img_path), aug_img)

            with out_lbl_path.open("w") as fh:
                for cls, (cx, cy, bw, bh) in zip(aug_labels, aug_boxes):
                    fh.write(f"{cls} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")

            count += 1

    return count


def _augment_with_opencv(
    images_dir: Path,
    output_images_dir: Path,
) -> int:
    """
    Basic augmentation using only OpenCV (flip + brightness).

    No bounding-box adjustment is applied for the flip; use this only as a
    last resort when ``albumentations`` is unavailable.

    Parameters
    ----------
    images_dir:
        Source image directory.
    output_images_dir:
        Destination directory for augmented files.

    Returns
    -------
    Number of augmented images written.
    """
    import cv2  # local import

    output_images_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    image_files = (
        list(images_dir.glob("*.jpg"))
        + list(images_dir.glob("*.jpeg"))
        + list(images_dir.glob("*.png"))
    )

    for img_path in image_files:
        image = cv2.imread(str(img_path))
        if image is None:
            continue

        stem = img_path.stem

        # 1. Horizontal flip
        flipped = cv2.flip(image, 1)
        cv2.imwrite(
            str(output_images_dir / f"{stem}{AUGMENTED_SUFFIX}_flip.jpg"),
            flipped,
        )
        count += 1

        # 2. Brightness increase (+40)
        bright = cv2.convertScaleAbs(image, alpha=1.0, beta=40)
        cv2.imwrite(
            str(output_images_dir / f"{stem}{AUGMENTED_SUFFIX}_bright.jpg"),
            bright,
        )
        count += 1

        # 3. Brightness decrease (−40)
        dark = cv2.convertScaleAbs(image, alpha=1.0, beta=-40)
        cv2.imwrite(
            str(output_images_dir / f"{stem}{AUGMENTED_SUFFIX}_dark.jpg"),
            dark,
        )
        count += 1

    return count


def augment_dataset(dataset_root: Path = DATASET_ROOT) -> None:
    """
    Augment all training images in the dataset.

    Tries ``albumentations`` first for label-aware augmentation; falls back
    to plain OpenCV transforms if it is not installed.

    Augmented files are saved alongside the originals (same ``train``
    directories) with the ``_aug`` suffix so they are picked up automatically
    by YOLOv8's data loader.

    Parameters
    ----------
    dataset_root:
        Root directory of the dataset.
    """
    images_train = dataset_root / "images" / "train"
    labels_train = dataset_root / "labels" / "train"

    if not images_train.is_dir():
        print(f"[ERROR] Training images directory not found: {images_train}")
        print("[INFO] Run with no flags to see download instructions.")
        return

    n_before = _count_images(images_train)
    print(f"\n[INFO] Augmenting dataset ({n_before} training images) …")

    # Try albumentations first
    try:
        import albumentations  # noqa: F401 — just checking availability

        count = _augment_with_albumentations(
            images_dir=images_train,
            labels_dir=labels_train,
            output_images_dir=images_train,   # save back into train/
            output_labels_dir=labels_train,
        )
        print(f"[INFO] Augmentation (albumentations): {count} new images created.")

    except ImportError:
        print(
            "[WARNING] 'albumentations' not installed.  "
            "Falling back to basic OpenCV augmentation."
        )
        print("[TIP] For better results: pip install albumentations")
        count = _augment_with_opencv(
            images_dir=images_train,
            output_images_dir=images_train,
        )
        print(f"[INFO] Augmentation (OpenCV fallback): {count} new images created.")

    n_after = _count_images(images_train)
    print(f"[INFO] Training set size: {n_before} → {n_after} images.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Dataset helper for the zebra-crossing detection project.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify dataset directory structure and exit.",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show dataset statistics (image counts, class names) and exit.",
    )
    parser.add_argument(
        "--augment",
        action="store_true",
        help="Augment training images and exit.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not attempt to open the Roboflow URL in a browser.",
    )
    parser.add_argument(
        "--dataset-dir",
        default=str(DATASET_ROOT),
        help=f"Path to dataset root (default: {DATASET_ROOT})",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()
    dataset_root = Path(args.dataset_dir)

    if args.verify:
        verify_dataset_structure(dataset_root)
        return

    if args.stats:
        show_dataset_stats(dataset_root)
        return

    if args.augment:
        augment_dataset(dataset_root)
        return

    # Default: print instructions and open browser
    print_download_instructions()

    if not args.no_browser:
        open_roboflow_browser()


if __name__ == "__main__":
    main()
