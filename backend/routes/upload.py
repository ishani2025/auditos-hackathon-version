# backend/routes/upload.py
"""
Upload blueprint (connector only).
Saves uploads -> website/static/uploads/
Copies accepted -> website/static/images/
Calls detect_screen and phash services (which contain thresholds/logic).
Uses phash_db (256-bit) for duplicate checks.
"""

import os
import sys
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import shutil

# ensure backend dir on path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.insert(0, backend_dir)

# Import services and DB (these modules hold their own defaults/logic)
from services.detect_screen import ScreenFraudDetector
from services.phash import phash_service
from models.dbp import phash_db

upload_bp = Blueprint("upload", __name__)

# File locations (website static folders)
UPLOADS_DIR = os.path.join(backend_dir, "website", "static", "uploads")
IMAGES_DIR = os.path.join(backend_dir, "website", "static", "images")
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

ALLOWED_EXT = { "png","jpg","jpeg","gif","bmp","webp" }

def allowed_file(fname):
    return "." in fname and fname.rsplit(".",1)[1].lower() in ALLOWED_EXT

def save_uploaded_file(file_storage):
    """Save original upload into uploads folder (keeps original filename, but made safe)."""
    safe = secure_filename(file_storage.filename)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique = uuid.uuid4().hex[:8]
    saved_name = f"{ts}_{unique}_{safe}"
    out_path = os.path.join(UPLOADS_DIR, saved_name)
    file_storage.save(out_path)
    return out_path, saved_name

def make_uuid_filename(orig_name):
    ext = orig_name.rsplit(".",1)[1] if "." in orig_name else "jpg"
    return f"{uuid.uuid4().hex[:12]}.{ext}"

def generate_credit_id():
    return f"EPR-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

# Create a detector instance (uses its internal defaults for thresholds)
screen_detector = ScreenFraudDetector()

@upload_bp.route("/upload", methods=["POST"])
def upload_image():
    # Validate file
    if "image" not in request.files:
        return jsonify({"error":"No file part 'image'"}), 400

    f = request.files["image"]
    if f.filename == "" or not allowed_file(f.filename):
        return jsonify({"error":"Invalid or missing filename/format"}), 400

    # Save to uploads (always)
    saved_path, saved_filename = save_uploaded_file(f)

    # Prepare response scaffolding (we will always include both checks)
    timestamp = datetime.utcnow().isoformat()

    # 1) Moiré detection (service decides thresholds & verdict)
    try:
        moire_result = screen_detector.detect(saved_path)
    except Exception as e:
        moire_result = {
            "fraud_detected": False,
            "score": 0.0,
            "fft_score": 0.0,
            "reason": f"Error running moire detector: {e}"
        }

    # 2) pHash fingerprint generation (service decides hash size)
    phash_hex = None
    phash_error = None
    try:
        phash_hex = phash_service.generate_from_path(saved_path)
        if not phash_hex:
            phash_error = "pHash generation returned no hash"
    except Exception as e:
        phash_error = f"Error generating pHash: {e}"

    # 3) Duplicate check via phash_db (expects 64-hex pHash)
    duplicate_info = {
        "is_duplicate": False,
        "total_checked": 0,
        "duplicates_found": 0,
        "closest_distance": None,
        "error": None
    }

    if phash_hex and len(phash_hex) >= 1:
        try:
            dup_res = phash_db.check_duplicate_256bit(phash_hex)
            # normalize returned structure
            duplicate_info["is_duplicate"] = dup_res.get("is_duplicate", False)
            duplicate_info["total_checked"] = dup_res.get("total_checked", 0)
            duplicate_info["duplicates_found"] = dup_res.get("duplicates_found", 0)
            if dup_res.get("closest_match"):
                duplicate_info["closest_distance"] = dup_res["closest_match"].get("distance")
            else:
                duplicate_info["closest_distance"] = None
            if dup_res.get("error"):
                duplicate_info["error"] = dup_res.get("error")
        except Exception as e:
            duplicate_info["error"] = f"Duplicate check error: {e}"
    else:
        duplicate_info["error"] = phash_error or "No pHash available"

    # 4) Combine final decision (upload.py does not set thresholds — it just combines boolean flags)
    reasons = []
    if moire_result.get("fraud_detected"):
        reasons.append("screen fraud")
    if duplicate_info.get("is_duplicate"):
        reasons.append("duplicate image")

    fraud = len(reasons) > 0
    accepted = not fraud

    credit_id = None
    stored_image_name = None

    # If accepted -> generate credit_id, store hash in phash_db and copy image to images folder with UUID name
    if accepted and phash_hex and len(phash_hex) == 64:
        credit_id = generate_credit_id()
        # store hash in DB (dbp expects 64-char hex)
        try:
            phash_db.store_256bit_hash(phash_hex, credit_id, "demo_website", saved_path, os.path.getsize(saved_path))
        except Exception:
            # try alias if any
            try:
                phash_db.store_hash(phash_hex, credit_id, "demo_website", saved_path, os.path.getsize(saved_path))
            except Exception:
                pass

        # copy to images folder with UUID filename to avoid collisions (Option B)
        stored_image_name = make_uuid_filename(saved_filename)
        dest_path = os.path.join(IMAGES_DIR, stored_image_name)
        try:
            shutil.copy(saved_path, dest_path)
        except Exception:
            stored_image_name = None

    # 5) Build UI-compatible response (new clean final_verdict shape)
    response = {
        "filename": saved_filename,
        "image_url": f"/static/uploads/{saved_filename}",
        "timestamp": timestamp,
        "final_verdict": {
            "fraud": fraud,
            "reasons": reasons,
            "accepted": accepted,
            "credit_id": credit_id
        },
        "checks": {
            "moire_detection": {
                "fraud_detected": bool(moire_result.get("fraud_detected", False)),
                "score": moire_result.get("score"),
                "fft_score": moire_result.get("fft_score"),
                "reason": moire_result.get("reason"),
                "verdict": "🚫 FRAUD" if moire_result.get("fraud_detected", False) else "✅ CLEAN"
            },
            "phash_duplicate": {
                "is_duplicate": duplicate_info.get("is_duplicate", False),
                "total_checked": duplicate_info.get("total_checked", 0),
                "duplicates_found": duplicate_info.get("duplicates_found", 0),
                "closest_distance": duplicate_info.get("closest_distance"),
                "error": duplicate_info.get("error"),
                "verdict": "🚫 DUPLICATE" if duplicate_info.get("is_duplicate", False) else ("⚠️ ERROR" if duplicate_info.get("error") else "✅ UNIQUE")
            }
        },
        # include phash for debugging (optional)
        "phash": phash_hex
    }

    # Always return 200 with structured JSON so frontend never sees HTML 404 or invalid date
    return jsonify(response), 200
