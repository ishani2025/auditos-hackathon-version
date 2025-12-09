import os
import hashlib
from typing import Optional, Dict, Any, Tuple

import cv2
import numpy as np
# Assuming 'models.dbm' exists in your environment, otherwise comment this import out
from models.dbm import fraud_db 

class ScreenFraudDetector:
    """
    Forensic Screen Detector v2.2
    - Check 1: Laplacian Variance (Texture Analysis)
      -> Real 3D objects have HIGH variance.
      -> Digital screens/Blurs have LOW variance.
    - Check 2: FFT (Frequency Domain)
      -> Detects pixel grids. Now includes 'Spike Ratio' to ignore woven bags.
    """

    def __init__(self, blur_threshold: float = 50.0, fft_threshold: float =15.0):
        # Increased blur_threshold to 50.0 to safely categorize the bag (Score ~28) as "Low Texture"
        self.blur_threshold = blur_threshold
        self.fft_threshold = fft_threshold

    def detect(self, image_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        result = {
            "fraud_detected": False,
            "score": 0.0,
            "fft_score": 0.0,
            "reason": "",
            "image_hash": self._hash_file(image_path),
        }

        if not os.path.exists(image_path):
            result["reason"] = f"File not found: {image_path}"
            return result

        try:
            img = cv2.imread(image_path)
            if img is None:
                result["reason"] = "Failed to load image"
                return result

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # --- CHECK 1: Laplacian Variance (Texture) ---
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var() #type:ignore
            result["score"] = laplacian_var

            # LOGIC CHANGE: We strictly separate "Blurry" from "High Texture"
            if laplacian_var < self.blur_threshold:
                # Case A: Image is Smooth/Blurry (Like the Bag with score 28)
                # We do NOT run FFT here. A blurry image cannot have a sharp pixel grid.
                # Running FFT on blurry noise causes False Positives (like the bag weave).
                
                if laplacian_var < 5.0:
                    result["fraud_detected"] = True
                    result["reason"] = f"FRAUD: Image is completely flat/digital (Score: {laplacian_var:.2f})"
                else:
                    result["fraud_detected"] = False
                    result["reason"] = f"WARNING: Image is blurry or low light (Score: {laplacian_var:.2f})"
                    # FFT IS SKIPPED HERE TO PROTECT REAL BLURRY OBJECTS
            else:
                # Case B: High Texture (Could be Real Trash OR a Sharp Screen)
                # Now we run the Forensic FFT check.
                is_screen_grid, fft_score = self._analyze_screen_frequency(gray)
                result["fft_score"] = fft_score

                if is_screen_grid:
                    result["fraud_detected"] = True
                    result["reason"] = f"FRAUD: Screen Grid Pattern Detected (FFT Score: {fft_score:.2f})"
                else:
                    result["fraud_detected"] = False
                    result["reason"] = f"Pass. Natural 3D texture detected (Lap: {laplacian_var:.0f}, FFT: {fft_score:.2f})"

            # Log to DB (Mock)
            # log_payload = ... (omitted for brevity)

        except Exception as e:
            result["reason"] = f"Detection error: {e}"

        return result

    def _analyze_screen_frequency(self, gray_img) -> Tuple[bool, float]:
        """
        Analyzes image for periodic pixel grids using FFT and Peak Sharpness.
        """
        # 1. Resize
        target_size = (512, 512)
        img_resized = cv2.resize(gray_img, target_size)

        # 2. FFT
        f = np.fft.fft2(img_resized)
        fshift = np.fft.fftshift(f)
        magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1)

        # 3. Mask the Center (Low Frequencies)
        rows, cols = img_resized.shape
        crow, ccol = rows // 2, cols // 2
        r = 80 # Aggressive mask to ignore general shapes
        magnitude_spectrum[crow-r:crow+r, ccol-r:ccol+r] = 0

        # 4. Find the Strongest Peak
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(magnitude_spectrum)
        mean_noise = np.mean(magnitude_spectrum)
        fft_score = max_val - mean_noise

        # 5. NEW: Check Peak Sharpness (The "Bag Filter")
        # Real screens have sharp "spikes" (1-2 pixels wide). 
        # Woven bags have "hills" (clustered peaks).
        y, x = max_loc
        
        # Get a 9x9 window around the peak
        y1, y2 = max(0, y - 4), min(rows, y + 5)
        x1, x2 = max(0, x - 4), min(cols, x + 5)
        
        neighborhood = magnitude_spectrum[y1:y2, x1:x2]
        neighborhood_sum = np.sum(neighborhood)
        neighborhood_count = neighborhood.size
        
        # Calculate ratio of Peak to its neighbors
        if neighborhood_count > 1:
            # Average height of the "hill" excluding the peak
            surrounding_mean = (neighborhood_sum - max_val) / (neighborhood_count - 1)
            
            # Ratio: Screen Spikes are > 1.10x higher than their immediate neighbors
            # Bag Hills are flatter (~1.0x - 1.05x)
            spike_ratio = max_val / (surrounding_mean + 1e-5)
        else:
            spike_ratio = 0.0

        # If the peak isn't sharp, it's just texture. Kill the score.
        is_sharp_peak = spike_ratio > 1.10
        
        if not is_sharp_peak:
            fft_score = 0.0

        is_screen = bool(fft_score > float(self.fft_threshold))

        return is_screen, float(fft_score)

    def _hash_file(self, path: str) -> str:
        try:
            h = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return "unknown_hash"

screen_detector = ScreenFraudDetector()

# --- Main Execution Block ---
if __name__ == "__main__":
    import sys
    
    # Tuned Thresholds:
    # blur_threshold=50.0 (Bag is ~28, so it falls into "Blurry/Safe" category)
    # fft_threshold=15.0 (Screens score > 15)
    screen_detector = ScreenFraudDetector(blur_threshold=50.0, fft_threshold=15.0)

    if len(sys.argv) < 2:
        print("Usage: python detect_screen.py <image_path>")
        # Hardcode for testing if needed
        # sys.argv = ["detect_screen.py", "images/trashpica.jpeg"] 
        sys.exit(1)

    path = sys.argv[1]
    if os.path.exists(path):
        res = screen_detector.detect(path)
        print("\n" + "="*50)
        print(f"🔎 ANALYSIS RESULT FOR: {os.path.basename(path)}")
        print("="*50)
        print(f"Fraud Detected : {res['fraud_detected']}")
        print(f"Reason         : {res['reason']}")
        print("-" * 20)
        print(f"Laplacian Score: {res['score']:.2f}")
        print(f"FFT Grid Score : {res['fft_score']:.2f}")
        print("="*50 + "\n")
    else:
        print(f"File not found: {path}")