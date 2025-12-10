# backend/test_all_pairs_comparison.py

import sys
import os
import glob
from typing import List, Tuple, Dict

# ---------------------------------------
# PATH SETUP
# ---------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = current_dir
sys.path.insert(0, backend_dir)

# ---------------------------------------
# IMPORT PURE PHASH SERVICE ONLY
# ---------------------------------------
try:
    from services.phash import phash_service  # global instance
    DEFAULT_THRESHOLD = phash_service.default_threshold
    print(f"✅ Pure pHash loaded. Default threshold = {DEFAULT_THRESHOLD}")

except ImportError as e:
    print("❌ ERROR: Could not import PurePhashService.")
    print("Details:", e)
    sys.exit(1)

# ---------------------------------------
# DIRECTORY WHERE TEST IMAGES ARE STORED
# ---------------------------------------
IMAGE_DIR = os.path.join(backend_dir, "images")

# ---------------------------------------
# HELPER: LOAD TEST IMAGES
# ---------------------------------------
def get_all_test_images(directory_path) -> List[Tuple[str, str]]:
    """Return list of (filename, file_path)."""
    if not os.path.isdir(directory_path):
        print(f"❌ Image directory not found: {directory_path}")
        return []

    extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']
    image_paths = []

    for ext in extensions:
        image_paths.extend(glob.glob(os.path.join(directory_path, ext)))

    return [(os.path.basename(p), p) for p in sorted(image_paths)]

# ---------------------------------------
# MAIN TEST FUNCTION
# ---------------------------------------
def run_all_pairs_comparison():
    print("\n🧪 Testing All-Pairs pHash Comparison (PURE pHash)")
    print("=" * 65)

    # Load images
    images = get_all_test_images(IMAGE_DIR)

    if len(images) < 2:
        print("❌ Need at least 2 images to compare.")
        return

    print(f"🖼️ Found {len(images)} images:")
    for name, _ in images:
        print(f"  - {name}")

    # Generate hashes
    print("\n🔑 Generating pHashes...")
    hashes: Dict[str, str] = {}

    for name, path in images:
        img_hash = phash_service.generate_from_path(path)

        if img_hash:
            print(f"🔑 {name}: {img_hash} ({len(img_hash)} chars)")
            hashes[name] = img_hash
        else:
            print(f"❌ Failed to generate hash for {name}")

    if len(hashes) != len(images):
        print("❌ At least one hash failed. Stopping.")
        return

    # Use ONLY the service threshold (NOT database)
    threshold = DEFAULT_THRESHOLD
    print(f"\n🔬 Performing comparisons (Threshold = {threshold})")

    results: List[Tuple[str, str, int, bool]] = []
    names = list(hashes.keys())

    # Compare every pair
    for i in range(len(names)):
        for j in range(i, len(names)):
            name1 = names[i]
            name2 = names[j]

            hash1 = hashes[name1]
            hash2 = hashes[name2]

            is_similar, distance = phash_service.compare(hash1, hash2, threshold)

            print("\n🔍 Hash Comparison:")
            print(f"   A: {name1}")
            print(f"   B: {name2}")
            print(f"   Hash A: {hash1}")
            print(f"   Hash B: {hash2}")
            print(f"   Distance: {distance}")
            print(f"   Similar? (<= {threshold}): {is_similar}")

            results.append((name1, name2, distance, is_similar))

    # Print results table
    print("\n" + "=" * 65)
    print("ALL PAIRS COMPARISON RESULTS")
    print("-" * 65)

    col_width = 20
    print(
        f"{'Image A':<{col_width}}"
        f"{'Image B':<{col_width}}"
        f"{'Distance':<12}"
        f"{'Similar?':<10}"
    )
    print("-" * 65)

    for name1, name2, dist, sim in results:
        status = "YES ✅" if sim else "NO ❌"
        print(
            f"{name1:<{col_width}}"
            f"{name2:<{col_width}}"
            f"{dist:<12}"
            f"{status:<10}"
        )

    print("=" * 65)
    print("✅ All-Pairs Test Complete.\n")


# ---------------------------------------
# RUN DIRECTLY
# ---------------------------------------
if __name__ == "__main__":
    run_all_pairs_comparison()
