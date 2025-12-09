# C:\Users\svars\auditos\auditos\backend\test_all_pairs_comparison.py

import sys
import os
import glob
from typing import List, Tuple, Dict

# --- Setup Path ---
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = current_dir
sys.path.insert(0, backend_dir)

# --- Direct Imports of Services and Models ---
try:
    # Import the service for hashing
    from services.phash import phash_service 
    # Import the database model to get the configured default threshold
    # NOTE: Assuming 'models.dbp' contains a class 'PhashDatabase' with 'DEFAULT_THRESHOLD'
    from models.dbp import PhashDatabase 
    
    # Use the threshold defined in the database model
    DEFAULT_THRESHOLD = PhashDatabase.DEFAULT_THRESHOLD
    
except ImportError as e:
    print(f"❌ ERROR: Could not import necessary modules (phash_service or PhashDatabase). Check paths and dependencies.")
    print(f"Details: {e}")
    # Fallback to a value that catches B, C, and D if import fails
    DEFAULT_THRESHOLD = 135
    print(f"⚠️ Falling back to DEFAULT_THRESHOLD={DEFAULT_THRESHOLD} because model import failed.")
    # Exit here if the core service/model cannot be loaded
    # sys.exit(1) # Commented out exit to allow fallback test to proceed if needed

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


def run_all_pairs_comparison():
    """
    Executes the comprehensive all-pairs 256-bit pHash comparison, using 
    the threshold defined in the database model (dbp.py).
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
        print(f"   - {name}")

    # 2. Generate Hashes
    print("\n🔑 Generating 256-bit pHashes...")
    hashes: Dict[str, str] = {} # {filename: hash_string}
    
    for name, path in images:
        img_hash = phash_service.generate_from_path(path)
        if img_hash:
            # Added verbose hash printing
            print(f"🔑 Generated 256-bit pHash: {img_hash} ({len(img_hash)} chars)")
            hashes[name] = img_hash
        else:
            print(f"❌ Failed to generate hash for {name}. Skipping.")

    if len(hashes) != len(images):
        print("❌ Hashing failed for one or more images. Stopping.")
        return

    # 3. Perform All-Pairs Comparison
    
    current_threshold = DEFAULT_THRESHOLD # Use the imported threshold
    
    print(f"\n🔬 Performing All-Pairs Comparison (Threshold: {current_threshold}/256)...")
    
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
            is_similar, distance = phash_service.compare_256bit(hash1, hash2, current_threshold)
            
            # Re-added the detailed comparison logging for debugging/clarity
            print("🔍 Hash Comparison:")
            print(f"     Hash 1: {hash1}")
            print(f"     Hash 2: {hash2}")
            print(f"     Distance: {distance}/256")
            print(f"     Threshold: {current_threshold}")
            print(f"     Similar: {is_similar}")

            comparison_results.append((name1, name2, distance, is_similar))

    # 4. Report Results in Table Format
    
    print("\n" + "=" * 65)
    print("ALL-PAIRS COMPARISON RESULTS")
    print("-" * 65)
    
    # Define Column Widths
    col_width = 20
    
    # Print Header: Reflect the dynamic threshold
    print(f"{'Image A':<{col_width}}{'Image B':<{col_width}}{'Distance (0-256)':<18}{f'Similar (<= {current_threshold})':<15}")
    print("-" * 65)
    
    # Print Data
    for name1, name2, distance, is_similar in comparison_results:
        status = "✅ YES" if is_similar else "❌ NO"
        print(f"{name1:<{col_width}}{name2:<{col_width}}{distance:<18}{status:<15}")

    print("=" * 65)
    print("✅ All-Pairs Comparison Test Complete.")


if __name__ == "__main__":
    run_all_pairs_comparison()