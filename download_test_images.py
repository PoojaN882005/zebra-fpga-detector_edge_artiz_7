"""
Quick script to download zebra crossing test images from reliable public sources.
Run this before testing the model.
"""
import requests
import urllib3
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

os.makedirs("test_images", exist_ok=True)

# Use these direct image URLs (tested/reliable)
TEST_IMAGES = [
    # Zebra crossings (should detect)
    ("zebra1.jpg", "https://live.staticflickr.com/3760/9579613968_c06e2a3f53_b.jpg"),
    ("zebra2.jpg", "https://images.unsplash.com/photo-1572120360610-d971b9d7767c?w=640"),
    # Just roads (should NOT detect)
    ("road1.jpg", "https://images.unsplash.com/photo-1511407397940-d57f68e81203?w=640"),
]

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

for filename, url in TEST_IMAGES:
    dest = f"test_images/{filename}"
    if os.path.exists(dest):
        print(f"Already exists: {dest}")
        continue
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=20)
        if r.status_code == 200 and len(r.content) > 10000:
            with open(dest, "wb") as f:
                f.write(r.content)
            print(f"Downloaded: {dest} ({len(r.content)//1024} KB)")
        else:
            print(f"Failed {filename}: HTTP {r.status_code}, size {len(r.content)}")
    except Exception as e:
        print(f"Error {filename}: {e}")

print("\nDone. Check test_images/ folder.")
print("Now you can also just put any .jpg images of zebra crossings into test_images/ manually.")
