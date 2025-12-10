# backend/services/phash.py

from PIL import Image
import numpy as np
from typing import Optional, Tuple, List
import os
from io import BytesIO


class PurePhashService:
    """
    Industry-standard pure pHash implementation (DCT-based).
    Output = 256-bit hash (64 hex chars) using hash_size=16.
    """

    def __init__(self, hash_size: int = 16):
        if hash_size < 2:
            raise ValueError("hash_size must be >= 2")

        self.hash_size = hash_size                # 16 → 16x16 bits
        self.img_size = hash_size * 4            # 64x64 resized image
        self.total_bits = hash_size * hash_size  # 256 bits
        self.hex_len = self.total_bits // 4      # 64 hex digits

        # Recommended default threshold for 256-bit pHash
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
