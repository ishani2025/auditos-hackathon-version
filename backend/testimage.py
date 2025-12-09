# C:\Users\svars\auditos\auditos\backend\test_all_pairs_comparison.py

import sys
import os
import glob
from typing import List, Tuple, Dict

# --- Setup Path ---
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = current_dir
sys.path.insert(0, backend_dir)

# --- Direct Imports of Services ---
try:
    from services.phash import phash_service 
    # NOTE: We DO NOT import dbp.py, as we are only testing phash comparison logic here.
except ImportError as e:
    print(f"❌ ERROR: Could not import phash_service. Check paths and dependencies.")
    print(f"Details: {e}")
    sys.exit(1)

# --- Configuration ---
IMAGE_DIR = os.path.join(backend_dir, 'images')

# --- Helper Functions ---
def get_all_test_images(directory_path) -> List[Tuple[str, str]]:
    """Scans the directory and returns a list of (file_name, file_path) tuples."""
    if not os.path.isdir(directory_path):
        print(f"❌ Image directory not found: {directory_path}")
        return []

    extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']
    image_paths = []
    
    for ext in extensions:
        image_paths.extend(glob.glob(os.path.join(directory_path, ext)))
    
    # Return (filename, full_path) for cleaner output
    return [(os.path.basename(p), p) for p in sorted(image_paths)]


def run_all_pairs_comparison(default_threshold: int = 125):
    """
    Executes the comprehensive all-pairs 256-bit pHash comparison.
    """
    
    print("🧪 Testing All-Pairs 256-bit pHash Comparison (Service Layer Only)")
    print("=" * 65)
    
    # 1. Load Files
    images = get_all_test_images(IMAGE_DIR)
    
    if len(images) < 2:
        print(f"❌ Need at least 2 images in '{IMAGE_DIR}' for comparison!")
        sys.exit(1)

    print(f"🖼️ Found {len(images)} images for comparison in '{IMAGE_DIR}':")
    for name, _ in images:
        print(f"   - {name}")

    # 2. Generate Hashes
    print("\n🔑 Generating 256-bit pHashes...")
    hashes: Dict[str, str] = {} # {filename: hash_string}
    
    for name, path in images:
        img_hash = phash_service.generate_from_path(path)
        if img_hash:
            hashes[name] = img_hash
        else:
            print(f"❌ Failed to generate hash for {name}. Skipping.")

    if len(hashes) != len(images):
        print("❌ Hashing failed for one or more images. Stopping.")
        return

    # 3. Perform All-Pairs Comparison
    print(f"\n🔬 Performing All-Pairs Comparison (Threshold: {default_threshold}/256)...")
    
    all_names = list(hashes.keys())
    
    # Prepare results for structured output
    comparison_results: List[Tuple[str, str, int, bool]] = []
    
    for i in range(len(all_names)):
        name1 = all_names[i]
        hash1 = hashes[name1]
        
        # Compare with all images from i onwards (including self-to-self)
        for j in range(i, len(all_names)):
            name2 = all_names[j]
            hash2 = hashes[name2]
            
            # Use the core comparison logic from phash.py
            is_similar, distance = phash_service.compare_256bit(hash1, hash2, default_threshold)
            
            comparison_results.append((name1, name2, distance, is_similar))

    # 4. Report Results in Table Format
    
    print("\n" + "=" * 65)
    print("ALL-PAIRS COMPARISON RESULTS")
    print("-" * 65)
    
    # Define Column Widths
    col_width = 20
    
    # Print Header
    print(f"{'Image A':<{col_width}}{'Image B':<{col_width}}{'Distance (0-256)':<18}{'Similar (<= 125)':<15}")
    print("-" * 65)
    
    # Print Data
    for name1, name2, distance, is_similar in comparison_results:
        status = "✅ YES" if is_similar else "❌ NO"
        print(f"{name1:<{col_width}}{name2:<{col_width}}{distance:<18}{status:<15}")

    print("=" * 65)
    print("✅ All-Pairs Comparison Test Complete.")


if __name__ == "__main__":
    # NOTE: Setting the threshold to 125 here for testing, as discussed in the previous step.
    # The comparison logic still lives within phash.py.
    run_all_pairs_comparison(default_threshold=125)