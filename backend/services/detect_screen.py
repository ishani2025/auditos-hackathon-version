# backend/services/detect_screen.py
"""
Improved Screen Fraud Detector (drop-in replacement)

Features:
- Laplacian variance (texture)
- FFT-based multi-peak detection with spike-prominence
- Cross-channel peak overlap check (detects subpixel patterns)
- Adaptive thresholds and clear debug metrics for tuning
- All thresholds live here (upload.py remains a connector)
"""

import os
import hashlib
from typing import Optional, Dict, Any, Tuple, List

import cv2
import numpy as np

class ScreenFraudDetector:
    """
    PARAMETER GUIDE:
    
    blur_threshold (20.0):
        Laplacian variance below which image is considered low-texture.
        Images with score < 20 skip FFT analysis entirely.
        TYPICAL VALUES: Flat screens: <10, Blurry real: 20-100, Sharp real: 100+
    
    fft_score_threshold (50.0):
        Minimum FFT prominence required to consider a peak significant.
        Prominence = peak_height - mean_background_noise.
        TYPICAL VALUES: Screens: 50-200+, Printed text: 20-40
    
    spike_ratio_threshold (1.25):
        Ratio of peak height to surrounding neighborhood average.
        Sharp pixel grid spikes have ratio > 1.25.
        Printed text patterns have ratio closer to 1.0 (gradual hills).
    
    peak_count_threshold (2):
        Minimum number of distinct peaks needed to signal a grid pattern.
        Screens show multiple repeating peaks, single peaks may be noise.
    
    channel_overlap_threshold (0.4):
        Fraction of peaks that must appear across multiple color channels.
        Real screens show same pattern in R, G, B channels.
        Printed text often appears in only 1-2 channels.
    """
    def __init__(
        self,
        blur_threshold: float = 20.0,
        fft_score_threshold: float = 50.0,
        spike_ratio_threshold: float = 1.25,
        peak_count_threshold: int = 2,
        channel_overlap_threshold: float = 0.4
    ):
        """
        Thresholds (tunable inside this file):
          blur_threshold: laplacian variance below which image is considered low-texture (skip FFT).
          fft_score_threshold: base FFT prominence required for a candidate peak to be significant.
          spike_ratio_threshold: peak / neighbors ratio to ensure sharp spike.
          peak_count_threshold: minimum number of distinct peaks needed to signal a grid pattern.
          channel_overlap_threshold: fraction of peaks that must appear across multiple channels.
        """
        self.blur_threshold = blur_threshold
        self.fft_score_threshold = fft_score_threshold
        self.spike_ratio_threshold = spike_ratio_threshold
        self.peak_count_threshold = peak_count_threshold
        self.channel_overlap_threshold = channel_overlap_threshold

    def detect(self, image_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
           MAIN DETECTION PIPELINE:
           1. Load and validate image
           2. Laplacian texture analysis (fast filter)
           3. Multi-channel FFT analysis (detailed)
           4. Decision logic combining multiple signals
        5. Return comprehensive result with debug info
        """
        result = {
            "fraud_detected": False,
            "score": 0.0,         # Laplacian
            "fft_score": 0.0,     # aggregated fft prominence
            "reason": "",
            "image_hash": self._hash_file(image_path),
            # debug fields (helpful in UI)
            "debug": {}
        }

        if not os.path.exists(image_path):
            result["reason"] = f"File not found: {image_path}"
            return result

        try:
            bgr = cv2.imread(image_path)
            if bgr is None:
                result["reason"] = "Failed to load image"
                return result

            # Convert to grayscale for Laplacian
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())  # type: ignore
            result["score"] = laplacian_var

            # If too low texture → skip heavy FFT checks (very blurry)
            if laplacian_var < self.blur_threshold:
                result["fft_score"] = 0.0
                result["fraud_detected"] = False
                result["reason"] = f"Low texture / blurry (Lap: {laplacian_var:.2f})"
                result["debug"]["laplacian"] = laplacian_var
                return result

            # Run multichannel FFT analysis
            combined_metrics = self._multichannel_fft_analysis(bgr)
            result["debug"].update(combined_metrics)

            # Primary signals
            fft_score = float(combined_metrics.get("max_prominence", 0.0))
            spike_ratio = float(combined_metrics.get("spike_ratio", 0.0))
            peak_count = int(combined_metrics.get("peak_count", 0))
            overlap = float(combined_metrics.get("channel_overlap", 0.0))

            result["fft_score"] = fft_score

            # Decision rule (combined):
            # - need at least some FFT prominence,
            # - AND either multiple peaks with decent overlap across channels,
            # - OR a single extremely sharp spike.
            rule1 = (fft_score >= self.fft_score_threshold and peak_count >= self.peak_count_threshold and overlap >= self.channel_overlap_threshold)
            rule2 = (spike_ratio >= self.spike_ratio_threshold and fft_score >= (self.fft_score_threshold * 0.6))

            if rule1 or rule2:
                result["fraud_detected"] = True
                result["reason"] = f"FRAUD: Screen Grid Detected (FFT: {fft_score:.2f}, Peaks: {peak_count}, SpikeRatio: {spike_ratio:.2f}, Overlap: {overlap:.2f})"
            else:
                result["fraud_detected"] = False
                result["reason"] = f"Pass. Natural texture (Lap: {laplacian_var:.2f}, FFT: {fft_score:.2f}, Peaks: {peak_count}, Overlap: {overlap:.2f})"

            # fill debug
            result["debug"]["laplacian"] = laplacian_var
            result["debug"]["fft_score"] = fft_score
            result["debug"]["spike_ratio"] = spike_ratio
            result["debug"]["peak_count"] = peak_count
            result["debug"]["channel_overlap"] = overlap

        except Exception as e:
            result["reason"] = f"Detection error: {e}"

        return result

    def _multichannel_fft_analysis(self, bgr_img) -> Dict[str, Any]:
        """
        Compute FFT magnitude for each channel and a combined metric.
        Returns:
            {
                'channel_prominences': [rprom, gprom, bprom],
                'max_prominence': float,
                'spike_ratio': float,
                'peak_count': int,
                'channel_overlap': float,
                'peak_locations': [(y,x), ...]   # for top peaks in combined magnitude
            }
        """
        # ensure we have integer arrays
        img = bgr_img.copy()
        if img.ndim != 3 or img.shape[2] != 3:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        # standardize size for stable FFT
        target = (512, 512)
        img_resized = cv2.resize(img, target, interpolation=cv2.INTER_AREA)
        rows, cols = target

        # compute magnitude for each channel
        mags = []
        peaks_list = []
        for ch in range(3):
            channel = img_resized[:, :, ch].astype(np.float32)
            f = np.fft.fft2(channel)
            fshift = np.fft.fftshift(f)
            mag = 20 * np.log(np.abs(fshift) + 1.0)
            mags.append(mag)

        # combined magnitude (sum or mean)
        combined = np.mean(np.stack(mags, axis=0), axis=0)

        # mask center low frequencies aggressively
        crow, ccol = rows // 2, cols // 2
        r = int(min(rows, cols) * 0.12)  # 12% radius
        masked = combined.copy()
        masked[crow-r:crow+r, ccol-r:ccol+r] = 0.0

        # compute noise floor and max peak
        mean_noise = float(np.mean(masked))
        std_noise = float(np.std(masked))
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(masked)
        max_val = float(max_val)

        # compute prominence (difference to mean noise)
        prominence = max_val - mean_noise

        # find candidate peaks above adaptive threshold (mean + k*std)
        k = 2.2  # sensitivity factor for candidate peaks
        threshold = mean_noise + k * std_noise
        # Create a binary mask of candidate pixels
        cand_mask = (masked > threshold).astype(np.uint8)

        # find connected components / local maxima to count distinct peaks
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(cand_mask, connectivity=8)
        peak_centers = []
        for i in range(1, num_labels):
            # For each component get its maximum location (local peak)
            mask_i = (labels == i)
            if np.count_nonzero(mask_i) == 0:
                continue
            # compute peak value in this component
            comp_vals = masked * mask_i
            minv, maxv, minl, maxl = cv2.minMaxLoc(comp_vals.astype(np.float32))
            peak_centers.append((int(maxl[1]), int(maxl[0]), float(maxv)))  # (y,x,value)

        # sort peaks by value desc
        peak_centers.sort(key=lambda x: x[2], reverse=True)

        # Only keep peaks that are sufficiently separated and prominent
        final_peaks = []
        min_separation = 6  # pixels
        for y, x, val in peak_centers:
            too_close = False
            for yy, xx, vv in final_peaks:
                if abs(yy - y) <= min_separation and abs(xx - x) <= min_separation:
                    too_close = True
                    break
            if not too_close:
                final_peaks.append((y, x, val))

        peak_count = len(final_peaks)

        # For spike_ratio compute local neighborhood around the top peak (9x9)
        if final_peaks:
            top_y, top_x, top_val = final_peaks[0]
            y1, y2 = max(0, top_y - 4), min(rows, top_y + 5)
            x1, x2 = max(0, top_x - 4), min(cols, top_x + 5)
            neighborhood = masked[y1:y2, x1:x2]
            neigh_sum = float(np.sum(neighborhood))
            neigh_count = neighborhood.size
            # surrounding mean excluding top pixel
            surrounding_mean = (neigh_sum - top_val) / max(1.0, (neigh_count - 1))
            spike_ratio = float(top_val / (surrounding_mean + 1e-9))
        else:
            spike_ratio = 0.0
            top_y = top_x = 0
            top_val = 0.0

        # Cross-channel overlap: check if peaks are present in individual channel mags near same locations
        def find_channel_peaks(mag):
            # same thresholding approach per channel
            mmean = float(np.mean(mag))
            mstd = float(np.std(mag))
            thr = mmean + k * mstd
            mmask = (mag > thr).astype(np.uint8)
            nlabels, labs, s, cents = cv2.connectedComponentsWithStats(mmask, connectivity=8)
            centers = []
            for ii in range(1, nlabels):
                mask_i = (labs == ii)
                if np.count_nonzero(mask_i) == 0:
                    continue
                minv, maxv, minl, maxl = cv2.minMaxLoc((mag * mask_i).astype(np.float32))
                centers.append((int(maxl[1]), int(maxl[0]), float(maxv)))
            return centers

        channel_peaks = [find_channel_peaks(m) for m in mags]

        # measure how many of final_peaks are also found in at least two channels
        overlap_count = 0
        for (py, px, pv) in final_peaks:
            found_channels = 0
            for ch_peaks in channel_peaks:
                for cy, cx, cv in ch_peaks:
                    if abs(cy - py) <= 4 and abs(cx - px) <= 4:
                        found_channels += 1
                        break
            if found_channels >= 2:
                overlap_count += 1

        channel_overlap = (overlap_count / max(1, peak_count)) if peak_count > 0 else 0.0

        return {
            "channel_prominences": [float(np.max(m)) for m in mags],
            "max_prominence": prominence,
            "mean_noise": mean_noise,
            "std_noise": std_noise,
            "threshold_for_peaks": threshold,
            "peak_count": peak_count,
            "peak_locations": [(int(p[0]), int(p[1])) for p in final_peaks[:10]],
            "spike_ratio": spike_ratio,
            "channel_overlap": channel_overlap,
            "top_peak_val": float(top_val),
            "top_peak_coord": (int(top_y), int(top_x))
        }

    def _hash_file(self, path: str) -> str:
        try:
            h = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return "unknown_hash"

# Global instance with safe defaults (used by upload.py)
screen_detector = ScreenFraudDetector()
