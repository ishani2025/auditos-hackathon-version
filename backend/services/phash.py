# backend/services/phash.py
"""
PHASH SERVICE: Generates and compares image fingerprints
256-bit perceptual hashing (64-character hex string) for high-precision duplicate detection
"""

from PIL import Image
import imagehash
import numpy as np
from typing import Optional, Tuple, List
import os
from io import BytesIO

class PhashService:
    """Service for 256-bit perceptual hashing operations"""
    
    # DEFAULT HASH SIZE IS 16 (16x16 = 256 bits)
    def __init__(self, hash_size: int = 16): 
        """
        Initialize pHash service
        
        Args:
            hash_size: Size of hash matrix (16 = 16x16 = 256-bit hash)
        """
        self.hash_size = hash_size
    
    def generate_from_path(self, image_path: str) -> Optional[str]:
        """
        Generate 256-bit pHash from image file
        
        Returns:
            64-character hexadecimal string (256 bits)
        """
        try:
            if not os.path.exists(image_path):
                print(f"❌ Image not found: {image_path}")
                return None
            
            with Image.open(image_path) as img:
                return self._process_image_to_hash(img)
                
        except Exception as e:
            print(f"❌ Error generating pHash from path: {e}")
            return None
    
    def generate_from_bytes(self, image_bytes: bytes) -> Optional[str]:
        """Generate 256-bit pHash from image bytes"""
        try:
            img = Image.open(BytesIO(image_bytes))
            return self._process_image_to_hash(img)
            
        except Exception as e:
            print(f"❌ Error generating pHash from bytes: {e}")
            return None
    
    def _process_image_to_hash(self, img: Image.Image) -> Optional[str]:
        """Internal function to convert an opened image into a pHash string."""
        if img.mode != 'L':
            img = img.convert('L')
        
        phash_obj = imagehash.dhash(img, hash_size=self.hash_size)
        hash_str = str(phash_obj)
        expected_len = 64 # 256 bits / 4 bits per hex char = 64 hex chars
        
        if len(hash_str) != expected_len: 
             print(f"⚠️ Unexpected hash length: {len(hash_str)} chars. Expected {expected_len} for 256-bit hash.")
             # Fallback to manual conversion and padding to 64 hex chars
             binary_array = phash_obj.hash.flatten()
             binary_str = ''.join(['1' if bit else '0' for bit in binary_array])
             hash_str = hex(int(binary_str, 2))[2:].zfill(expected_len)
        
        print(f"🔑 Generated 256-bit pHash: {hash_str} ({len(hash_str)} chars)")
        return hash_str

    
    def compare_256bit(self, hash1: str, hash2: str, threshold: int = 35) -> Tuple[bool, int]:
        """
        Compare two 256-bit pHash strings (64 hex chars each)
        
        Args:
            threshold: Maximum allowed Hamming distance (0-256)
        """
        if not hash1 or not hash2:
            return False, 256
        
        # Ensure both are 64 characters (Crucial Fix)
        hash1 = hash1.zfill(64)[:64]
        hash2 = hash2.zfill(64)[:64]
        
        try:
            hash_obj1 = imagehash.hex_to_hash(hash1)
            hash_obj2 = imagehash.hex_to_hash(hash2)
            
            distance = hash_obj1 - hash_obj2
            is_similar = distance <= threshold
            
            print(f"🔍 Hash Comparison:")
            print(f"    Hash 1: {hash1}")
            print(f"    Hash 2: {hash2}")
            print(f"    Distance: {distance}/{256}")
            print(f"    Threshold: {threshold}")
            print(f"    Similar: {is_similar}")
            
            return is_similar, distance
            
        except Exception as e:
            print(f"❌ Error comparing 256-bit hashes: {e}. Falling back to manual distance.")
            return self._manual_hamming_distance(hash1, hash2, threshold, total_bits=256)
    
    def _manual_hamming_distance(self, hash1: str, hash2: str, threshold: int, total_bits: int) -> Tuple[bool, int]:
        """Manual Hamming distance calculation for hex strings"""
        if len(hash1) != len(hash2):
            return False, total_bits
        
        def hex_to_binary(hex_str):
            expected_len = len(hex_str) * 4 # 64 * 4 = 256
            try:
                return bin(int(hex_str, 16))[2:].zfill(expected_len)
            except ValueError:
                return '0' * expected_len 
        
        bin1 = hex_to_binary(hash1)
        bin2 = hex_to_binary(hash2)
        
        if len(bin1) != len(bin2) or len(bin1) == 0:
             return False, total_bits
        
        distance = sum(bit1 != bit2 for bit1, bit2 in zip(bin1, bin2))
        is_similar = distance <= threshold
        
        return is_similar, distance
    
    compare = compare_256bit
    
    def batch_compare(self, new_hash: str, existing_hashes: List[Tuple[str, str]], threshold: int = 35) -> dict:
        """Compare new 256-bit hash against multiple existing hashes"""
        # ... (logic remains the same, but calls compare_256bit which now expects 64 chars)
        
        results = {
            "is_duplicate": False,
            "closest_match": None,
            "closest_distance": 256,
            "total_checked": len(existing_hashes),
            "matches": []
        }
        
        for existing_hash, item_id in existing_hashes:
            is_similar, distance = self.compare_256bit(new_hash, existing_hash, threshold)
            
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

# Create a global instance for easy import (now 256-bit)
phash_service = PhashService()

def test_phash_service_256bit():
    """Simple test to confirm 256-bit generation is working."""
    print("🧪 Testing 256-bit pHash Service Initialization...")
    print("=" * 60)
    
    from io import BytesIO
    temp_img = Image.new('RGB', (100, 100), color = 'red')
    
    with BytesIO() as f:
        temp_img.save(f, format='JPEG')
        image_bytes = f.getvalue()
        test_hash = phash_service.generate_from_bytes(image_bytes)
    
    if test_hash and len(test_hash) == 64: # Check for 64 chars
        print(f"✅ Success: Generated hash has correct 64-character length: {test_hash}")
    else:
        print(f"❌ Failure: Hash length is incorrect or generation failed. Length: {len(test_hash) if test_hash else 'None'}")

if __name__ == "__main__":
    test_phash_service_256bit()