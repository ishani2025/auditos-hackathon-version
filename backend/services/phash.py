# backend/services/phash.py

from PIL import Image
import numpy as np
from typing import Optional, Tuple, List
import os
from io import BytesIO
"""
PURE PERCEPTUAL HASH (PHASH) IMPLEMENTATION

This is a true pHash (perceptual hash) implementation using DCT (Discrete Cosine Transform),
NOT to be confused with dHash (difference hash). This is industry-standard pHash.

HOW IT WORKS:
1. Convert image to grayscale
2. Resize to 64x64 (for hash_size=16)
3. Apply 2D Discrete Cosine Transform (DCT)
4. Take low-frequency 16x16 block (most important visual information)
5. Compare each value to median to create 256-bit binary hash
6. Compare using Hamming distance

KEY PROPERTIES:
- DCT-based: Captures frequency domain information (like JPEG compression)
- Perceptual: Resistant to resizing, format changes, compression
- 256-bit hash: 64 hex characters for high collision resistance

USAGE:
phash_service = PurePhashService()
hash_str = phash_service.generate_from_path("image.jpg")  # Returns 64-char hex
similar, distance = phash_service.compare(hash1, hash2, threshold=130)
"""

class PurePhashService:
    """
    Industry-standard pure pHash implementation (DCT-based).
    Output = 256-bit hash (64 hex chars) using hash_size=16.
    """

    def __init__(self, hash_size: int = 16):
        if hash_size < 2:
            raise ValueError("hash_size must be >= 2")

        self.hash_size = hash_size                
        self.img_size = hash_size * 4            
        self.total_bits = hash_size * hash_size  
        self.hex_len = self.total_bits // 4      
        self.default_threshold = 130

    # -------------------------------------------------
    # HASH GENERATION
    # -------------------------------------------------
    def generate_from_path(self, image_path: str) -> Optional[str]:
        try:
            if not os.path.exists(image_path):
                return None

            with Image.open(image_path) as img:
                return self._process_image_to_hash(img)

        except Exception:
            return None

    def generate_from_bytes(self, image_bytes: bytes) -> Optional[str]:
        try:
            img = Image.open(BytesIO(image_bytes))
            return self._process_image_to_hash(img)
        except Exception:
            return None

    # -------------------------------------------------
    # CORE PHASH IMPLEMENTATION
    # -------------------------------------------------
    def _process_image_to_hash(self, img: Image.Image) -> Optional[str]:
        try:
            # 1. Convert to grayscale
            if img.mode != "L":
                img = img.convert("L")

            # 2. Resize to normalized size
            img_resized = img.resize((self.img_size, self.img_size), Image.LANCZOS)
            arr = np.asarray(img_resized, dtype=np.float32)

            # 3. 2D DCT
            dct2 = self._dct2(arr)

            # 4. Low-frequency 16x16 block
            lowfreq = dct2[:self.hash_size, :self.hash_size]

            # 5. Median threshold
            median_val = np.median(lowfreq.flatten())

            # 6. Convert to bits
            bits = (lowfreq.flatten() > median_val).astype(int)
            binary_str = "".join(str(b) for b in bits)

            # 7. Convert to hex string (normalized to 64 hex chars)
            hex_str = hex(int(binary_str, 2))[2:].zfill(self.hex_len)

            return hex_str

        except Exception:
            return None

    # -------------------------------------------------
    # DCT IMPLEMENTATION
    # -------------------------------------------------
    """
    2D DISCRETE COSINE TRANSFORM (TYPE II)
    
    Mathematical operation: T @ block @ T.T
    Where T is the DCT coefficient matrix
    
    Why DCT for perceptual hashing?
    - Captures frequency distribution (like human visual system)
    - Concentrates energy in low frequencies (perceptually important)
    - Robust to compression (basis of JPEG)
    - Fast computation (O(n² log n))
    
    Returns: DCT coefficients (same shape as input)
    Low frequencies are in top-left corner
    """
    def _dct2(self, block: np.ndarray):
        
        if block.ndim != 2:
            raise ValueError("block must be 2D")

        n = block.shape[0]

        # handle rectangular arrays if needed
        if block.shape[1] != n:
            T1 = self._dct_matrix(block.shape[0])
            T2 = self._dct_matrix(block.shape[1])
            return T1 @ block @ T2.T

        T = self._dct_matrix(n)
        return T @ block @ T.T

    def _dct_matrix(self, n: int):
        k = np.arange(n).reshape(-1, 1)
        i = np.arange(n).reshape(1, -1)
        angle = (np.pi * k * (2 * i + 1)) / (2 * n)

        T = np.cos(angle)
        T[0, :] *= np.sqrt(1 / n)
        T[1:, :] *= np.sqrt(2 / n)
        return T

    # -------------------------------------------------
    # COMPARISON (HAMMING DISTANCE)
    # -------------------------------------------------
    """
    PHASH COMPARISON USING HAMMING DISTANCE:
    
    HAMMING DISTANCE = number of differing bits between two hashes
    
    THRESHOLD GUIDELINES (for 256-bit pHash):
    - 0-10:   Essentially identical (different compression/format)
    - 11-30:  Same image, minor differences (lighting, small crop)
    - 31-80:  Similar images (different angle, same object)
    - 81-130: Related images (same scene, different composition)
    - 131+ :  Different images
    
    Default threshold=130 (≈50% difference):
    - Allows significant perceptual changes
    - Catches resized, recompressed, watermarked versions
    - Good for duplicate detection with variations
    
    For stricter matching (e.g., exact duplicates): threshold=30
    For looser matching (e.g., similar objects): threshold=100
    """
    def _hex_to_binary_str(self, hex_str: str) -> str:
        hex_str = hex_str.strip().lstrip("0x")

        try:
            return bin(int(hex_str, 16))[2:].zfill(len(hex_str) * 4)
        except Exception:
            return "0" * (len(hex_str) * 4)

    def compare(self, hash1: str, hash2: str, threshold: Optional[int] = None) -> Tuple[bool, int]:
        """
        Compare two pHash hex strings (256-bit).
        Returns: (is_similar, hamming_distance)
        """

        if not hash1 or not hash2:
            return False, self.total_bits

        # Normalize both hashes to correct length
        h1 = hash1.lower().zfill(self.hex_len)[:self.hex_len]
        h2 = hash2.lower().zfill(self.hex_len)[:self.hex_len]

        b1 = self._hex_to_binary_str(h1)
        b2 = self._hex_to_binary_str(h2)

        if len(b1) != len(b2):
            return False, self.total_bits

        # Hamming distance
        distance = sum(c1 != c2 for c1, c2 in zip(b1, b2))

        if threshold is None:
            threshold = self.default_threshold

        is_similar = distance <= threshold
        return is_similar, distance

    # -------------------------------------------------
    # BATCH COMPARISON
    # -------------------------------------------------
    def batch_compare(self, new_hash: str, existing_list: List[Tuple[str, str]], threshold: Optional[int] = None):
        """
    BATCH COMPARISON FOR DUPLICATE DETECTION:
    
    Use case: Check if new upload matches any previously stored image
    
    Parameters:
    - new_hash: pHash of uploaded image
    - existing_list: List of (stored_hash, item_id) pairs
    - threshold: Similarity threshold (default=130)
    
    Returns comprehensive match information:
    - is_duplicate: True if any match found
    - matches: List of all similar images found
    - closest_match: ID of most similar image
    - closest_distance: Hamming distance to closest match
    
    Performance: O(n) where n = number of stored images
    Typical use: Check against thousands of previous uploads
    """
        results = {
            "is_duplicate": False,
            "closest_match": None,
            "closest_distance": self.total_bits,
            "total_checked": len(existing_list),
            "matches": []
        }

        for stored_hash, item_id in existing_list:
            is_similar, distance = self.compare(new_hash, stored_hash, threshold)

            if is_similar:
                results["matches"].append({
                    "id": item_id,
                    "hash": stored_hash,
                    "distance": distance
                })

            if distance < results["closest_distance"]:
                results["closest_distance"] = distance
                results["closest_match"] = item_id

        if results["matches"]:
            results["is_duplicate"] = True

        return results


# GLOBAL INSTANCE
phash_service = PurePhashService()
