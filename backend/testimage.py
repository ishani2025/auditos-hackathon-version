# test_real_images.py
"""
Test pHash with REAL images from your device, loaded from a directory.
"""

import sys
import os
import glob
from PIL import Image, ImageDraw
import tempfile
import shutil

# Add backend to path (assuming your structure is correct)
sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))

# Placeholder for phash_service, replace with your actual import
# Assuming a structure like:
# .
# ├── backend
# │   └── services
# │       └── phash.py
# └── test_real_images.py
#
# from services.phash import phash_service 
# Since I cannot run your environment, I will use a dummy service
# You MUST replace this block with your actual phash_service import:
class DummyPhashService:
    @staticmethod
    def generate_from_path(path):
        # Dummy implementation: returns a hash based on file size for testing logic
        size = os.path.getsize(path)
        return f"{size:016x}"

    @staticmethod
    def compare(hash1, hash2, threshold=10):
        # Dummy Hamming Distance for testing logic (based on hash length difference)
        distance = abs(len(hash1) - len(hash2)) 
        return distance <= threshold, distance

try:
    # Attempt to use the actual service if available
    from services.phash import phash_service
except ImportError:
    # Fallback to the dummy service if the environment is not set up
    print("⚠️ WARNING: Could not import real phash_service. Using dummy service.")
    phash_service = DummyPhashService()
# --- End of phash_service placeholder ---

def get_image_paths_from_directory(directory_path='images'):
    """
    Scans a directory for common image file types and returns their paths.
    """
    
    # Ensure the directory exists
    if not os.path.isdir(directory_path):
        print(f"❌ Image directory not found: {directory_path}")
        print("Please create this folder and place your images inside.")
        return []

    # Supported file extensions
    extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']
    image_paths = []
    
    print(f"📁 Scanning directory: {os.path.abspath(directory_path)}")

    for ext in extensions:
        # Use glob to find all files matching the pattern
        full_pattern = os.path.join(directory_path, ext)
        # Using sorted for deterministic order
        image_paths.extend(sorted(glob.glob(full_pattern)))
        
    if not image_paths:
        print("💡 No images found. Please check the directory and file extensions.")
    
    return image_paths

def test_with_generated_images():
    """Test with programmatically created images (keep for isolated testing)"""
    print("🧪 Testing pHash with generated images...")
    print("=" * 60)
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    
    # Test 1: Two identical images
    print("\n🔍 Test 1: Two IDENTICAL images")
    # ... (rest of the identical image test logic) ...
    # Simplified creation for identical test
    img1_path = os.path.join(temp_dir, "identical1.jpg")
    img2_path = os.path.join(temp_dir, "identical2.jpg")
    img = Image.new('RGB', (800, 600), color='green')
    draw = ImageDraw.Draw(img)
    draw.text((100, 100), "Trash Pile #001", fill='white')
    img.save(img1_path)
    img.save(img2_path) # Save same content again
    
    hash1 = phash_service.generate_from_path(img1_path)
    hash2 = phash_service.generate_from_path(img2_path)
    print(f"   Image 1 Hash: {hash1}")
    print(f"   Image 2 Hash: {hash2}")
    similar, distance = phash_service.compare(hash1, hash2)
    print(f"   Distance: {distance}, Similar: {similar}")
    print(f"   Result: {'✅ IDENTICAL' if distance == 0 else '⚠️ Different'}")
    
    # ... (Test 2: Similar images and Test 3: Different images logic) ...
    
    # Cleanup (moved to the end of test_with_generated_images)
    try:
        shutil.rmtree(temp_dir)
    except Exception as e:
        print(f"Cleanup failed: {e}")

    print("\n" + "=" * 60)
    print("✅ Generated images test completed!")

def test_with_your_images(image_paths):
    """Test with your own images"""
    print("\n🧪 Testing with YOUR images...")
    print("=" * 60)
    
    if not image_paths:
        print("💡 No images found in the specified directory. Skipping comparison.")
        return
        
    hashes = []
    
    for i, img_path in enumerate(image_paths, 1):
        try:
            hash_str = phash_service.generate_from_path(img_path)
            if hash_str:
                hashes.append((img_path, hash_str))
                print(f"📸 Image {i}: {os.path.basename(img_path)}")
                print(f"   Hash: {hash_str}")
                print(f"   Size: {os.path.getsize(img_path)} bytes")
        except Exception as e:
            print(f"❌ Error processing {img_path}: {e}")
    
    # Compare all combinations
    if len(hashes) >= 2:
        print("\n🔍 Comparing images...")
        for i in range(len(hashes)):
            for j in range(i+1, len(hashes)):
                img1, hash1 = hashes[i]
                img2, hash2 = hashes[j]
                
                similar, distance = phash_service.compare(hash1, hash2)
                
                print(f"\n   {os.path.basename(img1)} vs {os.path.basename(img2)}:")
                print(f"   Distance: {distance}")
                print(f"   Similar: {similar}")
                
                if distance == 0:
                    print(f"   ⚠️  WARNING: Images are IDENTICAL!")
                elif similar:
                    print(f"   ⚠️  WARNING: Images are SIMILAR (possible duplicate)")
                else:
                    print(f"   ✅ Images are UNIQUE")

def main():
    """Main test function"""
    print("🖼️  REAL IMAGE pHash TESTER")
    print("=" * 60)
    
    # Run the automated tests first
    test_with_generated_images()
    
    # --- Load your real images from the directory ---
    IMAGE_DIR = 'backend/images'
    print(f"\n--- Testing with Real Images from **./{IMAGE_DIR}** ---")
    
    # 1. Get the list of images from the directory
    your_images_paths = get_image_paths_from_directory(IMAGE_DIR)
    
    # 2. Run the comparison test
    test_with_your_images(your_images_paths)
    
    print("\n✅ Real image testing completed!")

if __name__ == "__main__":
    main()