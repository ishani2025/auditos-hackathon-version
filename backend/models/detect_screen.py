import os
import hashlib
from typing import Optional, Dict, Any, Tuple

import cv2
import numpy as np
# Assuming 'models.dbm' exists in your environment, otherwise comment this import out
from models.dbm import fraud_db 

class ScreenFraudDetector:
    """
    Forensic Screen Detector v2.1
    - Check 1: Laplacian Variance (Texture Analysis)
      -> Detects if image is too blurry/flat (Digital/Screenshot).
    - Check 2: FFT (Frequency Domain)
      -> Detects unnatural grid patterns (Moiré) typical of photographing a pixel grid.
      -> Solves False Negatives on high-texture objects (like trash).
    """

    def __init__(self, blur_threshold: float = 100.0, fft_threshold: float = 15.0):
        """
        :param blur_threshold: Variance below this is considered 'Flat/Digital/Blurry'
        :param fft_threshold: FFT Peak-to-Noise ratio above this indicates a Pixel Grid.
        """
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
            # Measures how "rough" the image is.
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()#type:ignore
            result["score"] = laplacian_var

            if laplacian_var < self.blur_threshold:
                # Case A: Image is too smooth (Digital screenshot or blur)
                result["fraud_detected"] = True
                result["reason"] = (
                    f"POSSIBLE DIGITAL IMAGE. Low texture variance ({laplacian_var:.2f}). "
                )
            else:
                # --- CHECK 2: FFT Frequency Analysis (The Fix) ---
                # If texture is high (e.g. crumpled trash), we must check if 
                # that texture is natural or a pixel grid.
                is_screen_grid, fft_score = self._analyze_screen_frequency(gray)
                result["fft_score"] = fft_score

                if is_screen_grid:
                    # Case B: High texture, but it's artificial (Grid/Moire)
                    result["fraud_detected"] = True
                    result["reason"] = f"FRAUD: Screen Grid Pattern Detected (FFT Score: {fft_score:.2f})"
                else:
                    # Case C: High texture, random noise (Real 3D Object)
                    result["fraud_detected"] = False
                    result["reason"] = f"Pass. Natural 3D texture detected (Lap: {laplacian_var:.0f}, FFT: {fft_score:.2f})"

            # Log to DB (Mock)
            log_payload = {
                "image_hash": result["image_hash"],
                "laplacian_score": result["score"],
                "fft_score": result["fft_score"],
                "fraud_detected": result["fraud_detected"],
                "reason": result["reason"],
                "ip_address": (metadata or {}).get("ip_address", ""),
            }
            # fraud_db.log_screen_fraud(log_payload) # Uncomment if DB is connected

        except Exception as e:
            result["reason"] = f"Detection error: {e}"

        return result

    def _analyze_screen_frequency(self, gray_img) -> Tuple[bool, float]:
        """
        Performs FFT to detect periodic noise (Pixel Grids).
        1. Resizes image to 512x512 for consistent frequency scale.
        2. Masks center frequencies (natural shapes).
        3. Checks for high-frequency spikes (grids).
        """
        # 1. Resize to keep frequency scale consistent
        target_size = (512, 512)
        img_resized = cv2.resize(gray_img, target_size)

        # 2. Compute 2D FFT
        f = np.fft.fft2(img_resized)
        fshift = np.fft.fftshift(f)
        
        # Magnitude Spectrum (Log scale)
        # Add 1 to avoid log(0)
        magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1)

        # 3. Mask the Center (Low Frequencies)
        # We want to ignore the general shape of the trash/objects
        rows, cols = img_resized.shape
        crow, ccol = rows // 2, cols // 2
        r = 30 # Radius to mask
        
        magnitude_spectrum[crow-r:crow+r, ccol-r:ccol+r] = 0

        # 4. Calculate Score: Peak vs Average Noise
        max_peak = float(np.max(magnitude_spectrum))
        mean_noise = float(np.mean(magnitude_spectrum))
        
        # A high spike relative to background indicates a repetitive pattern
        fft_score = max_peak - mean_noise  # native Python float

        # 5. Determine if Screen
        is_screen = bool(fft_score > float(self.fft_threshold))

        return is_screen, fft_score

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
    
    # Initialize with tuned thresholds
    # blur_threshold=100 (Checks for flatness)
    # fft_threshold=15.0 (Checks for grids)
    screen_detector = ScreenFraudDetector(blur_threshold=100.0, fft_threshold=15.0)

    if len(sys.argv) < 2:
        print("Usage: python screen_fraud_detector.py <image_path>")
        # For testing within the script if no args provided:
        # sys.exit(1)
        test_path = "images/test1.jpeg" # Hardcoded for test
    else:
        test_path = sys.argv[1]

    if os.path.exists(test_path):
        res = screen_detector.detect(test_path)
        print("\n" + "="*50)
        print(f"🔎 ANALYSIS RESULT FOR: {os.path.basename(test_path)}")
        print("="*50)
        print(f"Fraud Detected : {res['fraud_detected']}")
        print(f"Reason         : {res['reason']}")
        print("-" * 20)
        print(f"Laplacian Score: {res['score']:.2f} (Target: >100 for Real)")
        print(f"FFT Grid Score : {res['fft_score']:.2f} (Target: <15 for Real)")
        print("="*50 + "\n")
    else:
        print(f"Test file not found: {test_path}")
