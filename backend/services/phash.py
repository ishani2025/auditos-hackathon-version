# Create unique fingerprint of image# backend/services/phash.py
"""
PHASH SERVICE: Generates and compares image fingerprints
This is the CORE of duplicate detection
"""

from PIL import Image
import imagehash
import numpy as np
from typing import Optional, Tuple
import os

class PhashService:
    """Service for perceptual hashing operations"""
    
    def __init__(self, hash_size: int = 8):
        """
        Initialize pHash service
        
        Args:
            hash_size: Size of hash (8 = 8x8 = 64-bit hash)
                      Higher = more accurate but slower
        """
        self.hash_size = hash_size
    
    def generate_from_path(self, image_path: str) -> Optional[str]:
        """
        Generate pHash from image file path
        
        Args:
            image_path: Path to image file
            
        Returns:
            16-character hex string or None if error
            
        Example:
            Input: "trash_pile.jpg"
            Output: "a1b2c3d4e5f6a1b2"
        """
        try:
            if not os.path.exists(image_path):
                print(f"❌ Image not found: {image_path}")
                return None
            
            # Open and process image
            with Image.open(image_path) as img:
                # Convert to grayscale for consistent hashing
                if img.mode != 'L':
                    img = img.convert('L')
                
                # Generate perceptual hash
                phash_obj = imagehash.phash(img, hash_size=self.hash_size)
                
                # Convert to hexadecimal string (16 chars for 64 bits)
                hash_str = str(phash_obj)
                
                # Ensure proper length
                if len(hash_str) != 16:
                    # Convert binary array to hex
                    binary_str = ''.join(['1' if bit else '0' for bit in phash_obj.hash.flatten()])
                    hash_str = hex(int(binary_str, 2))[2:].zfill(16)
                
                print(f"🔑 Generated pHash: {hash_str[:16]}... ({len(hash_str)} chars)")
                return hash_str
                
        except Exception as e:
            print(f"❌ Error generating pHash: {e}")
            return None
    
    def generate_from_bytes(self, image_bytes: bytes) -> Optional[str]:
        """
        Generate pHash directly from image bytes
        
        Args:
            image_bytes: Raw image data
            
        Returns:
            pHash string or None
        """
        try:
            from io import BytesIO
            img = Image.open(BytesIO(image_bytes))
            
            # Convert to grayscale
            if img.mode != 'L':
                img = img.convert('L')
            
            phash_obj = imagehash.phash(img, hash_size=self.hash_size)
            return str(phash_obj)
        except Exception as e:
            return None
    
    def compare(self, hash1: str, hash2: str, threshold: int = 10) -> Tuple[bool, int]:
        """
        Compare two pHash strings
        
        Args:
            hash1: First hash string
            hash2: Second hash string
            threshold: Maximum allowed difference (0-64)
                    0 = identical, 64 = completely different
                    Recommended: 10 for trash piles
            
        Returns:
            (is_similar, hamming_distance)
            
        Example:
            hash1 = "a1b2c3d4e5f6..."
            hash2 = "a1b2c3d4e5f7..."  # 1 character different
            → hamming_distance = 1
            → is_similar = True (if threshold=10)
        """
        if not hash1 or not hash2:
            return False, 64  # Max distance if missing
        
        try:
            # Convert hex strings to imagehash objects
            hash_obj1 = imagehash.hex_to_hash(hash1[:16])  # Use first 16 chars
            hash_obj2 = imagehash.hex_to_hash(hash2[:16])
            
            # Calculate Hamming distance (number of different bits)
            distance = hash_obj1 - hash_obj2
            
            # Check if similar (within threshold)
            is_similar = distance <= threshold
            
            return is_similar, distance
            
        except Exception as e:
            print(f"❌ Error comparing hashes: {e}")
            return False, 64
    
    def batch_compare(self, new_hash: str, existing_hashes: list) -> dict:
        """
        Compare new hash against multiple existing hashes
        
        Args:
            new_hash: New image's hash
            existing_hashes: List of (hash_string, item_id) tuples
            
        Returns:
            dict with results
        """
        results = {
            "is_duplicate": False,
            "closest_match": None,
            "closest_distance": 64,
            "total_checked": len(existing_hashes),
            "matches": []
        }
        
        for existing_hash, item_id in existing_hashes:
            is_similar, distance = self.compare(new_hash, existing_hash)
            
            if is_similar:
                results["matches"].append({
                    "hash": existing_hash,
                    "id": item_id,
                    "distance": distance
                })
                
                if distance < results["closest_distance"]:
                    results["closest_distance"] = distance
                    results["closest_match"] = item_id
        
        if results["matches"]:
            results["is_duplicate"] = True
        
        return results

# Create a global instance for easy import
phash_service = PhashService()

# Quick test function
def test_phash():
    """Test the pHash service"""
    print("🧪 Testing pHash Service...")
    
    # Create a simple test image
    from PIL import Image, ImageDraw
    import tempfile
    
    # Create two similar images
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp1:
        img1 = Image.new('RGB', (800, 600), color='green')
        draw = ImageDraw.Draw(img1)
        draw.text((100, 100), "Trash Pile Demo", fill='white')
        img1.save(tmp1.name)
        path1 = tmp1.name
    
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp2:
        img2 = Image.new('RGB', (800, 600), color='green')
        draw = ImageDraw.Draw(img2)
        draw.text((105, 105), "Trash Pile Demo", fill='white')  # Slight offset
        img2.save(tmp2.name)
        path2 = tmp2.name
    
    # Generate hashes
    hash1 = phash_service.generate_from_path(path1)
    hash2 = phash_service.generate_from_path(path2)
    
    print(f"📊 Hash 1: {hash1}")
    print(f"📊 Hash 2: {hash2}")
    
    # Compare
    similar, distance = phash_service.compare(hash1, hash2)
    print(f"\n🔍 Comparison:")
    print(f"   Distance: {distance}")
    print(f"   Similar: {similar}")
    print(f"   Verdict: {'DUPLICATE' if similar else 'UNIQUE'}")
    
    # Cleanup
    os.unlink(path1)
    os.unlink(path2)
    
    print("\n✅ pHash Service test completed!")

if __name__ == "__main__":
    test_phash()