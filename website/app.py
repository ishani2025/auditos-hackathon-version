# website/app.py
"""
AUDITOS DEMO WEBSITE - Showcases Backend Fraud Detection
Upload an image → See moiré + dHash results in real-time
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import uuid
import shutil
import datetime  # CHANGED: Import entire module
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend'))

# Import YOUR backend services
try:
    from backend.services.detect_screen import *
    from backend.services.dhash import *
    from backend.models.dbd import *
    from backend.models.dbm import *
    
    BACKEND_AVAILABLE = True
    print("✅ Loaded all backend services!")
except ImportError as e:
    print(f"⚠️ Backend import error: {e}")
    BACKEND_AVAILABLE = False

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'website/static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Create folders
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('website/static/images', exist_ok=True)

# Home page - Upload form
@app.route('/')
def index():
    return render_template('index.html')

# Upload endpoint
@app.route('/upload', methods=['POST'])
def upload():
    """Handle image upload and run fraud detection"""
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file"}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        # Generate unique filename
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
        filename = f"{uuid.uuid4()}.{file_ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save uploaded file
        file.save(filepath)
        
        print(f"📸 Uploaded: {filename}")
        
        # Run fraud detection
        results = run_fraud_detection(filepath, filename)
        
        # Also copy to images folder for dHash comparisons
        shutil.copy(filepath, f"website/static/images/{filename}")
        
        return jsonify(results)
        
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return jsonify({"error": str(e)}), 500

def run_fraud_detection(image_path, filename):
    """Run both fraud detection algorithms"""
    results = {
        "filename": filename,
        "image_url": f"/static/uploads/{filename}",
        "timestamp": datetime.datetime.now().isoformat(),  # FIXED: datetime.datetime.now()
        "checks": {}
    }
    
    # 1. MOIRÉ DETECTION (Screen Fraud)
    if BACKEND_AVAILABLE:
        print("🔍 Running Moiré Detection...")
        moire_result = screen_detector.detect(image_path)
        results["checks"]["moire_detection"] = {
            "fraud_detected": moire_result["fraud_detected"],
            "score": moire_result["score"],
            "fft_score": moire_result["fft_score"],
            "reason": moire_result["reason"],
            "verdict": "🚫 FRAUD" if moire_result["fraud_detected"] else "✅ GENUINE"
        }
        
        # Log to database
        fraud_db.log_screen_fraud({
            "image_hash": moire_result["image_hash"],
            "score": moire_result["score"],
            "fft_score": moire_result["fft_score"],
            "fraud_detected": moire_result["fraud_detected"],
            "reason": moire_result["reason"],
            "ip_address": request.remote_addr,
            "device_info": {"user_agent": request.user_agent.string}
        })
    else:
        results["checks"]["moire_detection"] = {
            "error": "Backend service not available",
            "verdict": "⚠️ MOCK DATA"
        }
    
    # 2. dHASH DUPLICATE CHECK
    if BACKEND_AVAILABLE:
        print("🔍 Running dHash Duplicate Check...")
        
        # Generate dHash for new image
        new_hash = phash_service.generate_from_path(image_path)
        
        if new_hash:
            results["dhash"] = new_hash[:16] + "..."  # Truncate for display
            
            # Check against ALL images in database
            duplicate_result = phash_db.check_duplicate_256bit(new_hash)
            
            results["checks"]["dhash_duplicate"] = {
                "is_duplicate": duplicate_result.get("is_duplicate", False),
                "total_checked": duplicate_result.get("total_checked", 0),
                "duplicates_found": duplicate_result.get("duplicates_found", 0),
                "closest_distance": duplicate_result.get("closest_match", {}).get("distance", 256) if duplicate_result.get("closest_match") else 256,
                "verdict": "🚫 DUPLICATE" if duplicate_result.get("is_duplicate") else "✅ UNIQUE"
            }
            
            # Store in database if unique
            if not duplicate_result.get("is_duplicate"):
                credit_id = f"DEMO_CREDIT_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"  # FIXED
                phash_db.store_256bit_hash(
                    new_hash, credit_id, "demo_website", image_path, os.path.getsize(image_path)
                )
                results["credit_id"] = credit_id
        else:
            results["checks"]["dhash_duplicate"] = {
                "error": "Failed to generate dHash",
                "verdict": "⚠️ ERROR"
            }
    else:
        results["checks"]["dhash_duplicate"] = {
            "error": "Backend service not available",
            "verdict": "⚠️ MOCK DATA"
        }
    
    # 3. FINAL VERDICT
    fraud_detected = False
    for check in results["checks"].values():
        if check.get("fraud_detected") or check.get("is_duplicate"):
            fraud_detected = True
            break
    
    results["final_verdict"] = {
        "fraud": fraud_detected,
        "status": "🚫 REJECTED - FRAUD DETECTED" if fraud_detected else "✅ ACCEPTED - EPR CREDIT ISSUED",
        "color": "danger" if fraud_detected else "success"
    }
    
    return results

# Get all uploaded images
@app.route('/images')
def get_images():
    """Get list of all uploaded images"""
    images = []
    upload_dir = app.config['UPLOAD_FOLDER']
    
    if os.path.exists(upload_dir):
        for filename in os.listdir(upload_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                images.append({
                    "name": filename,
                    "url": f"/static/uploads/{filename}",
                    "size": os.path.getsize(os.path.join(upload_dir, filename))
                })
    
    return jsonify({"images": images})

# Get fraud logs
@app.route('/logs')
def get_logs():
    """Get recent fraud logs"""
    if BACKEND_AVAILABLE:
        logs = fraud_db.get_recent_logs(10)
        return jsonify({"logs": logs})
    return jsonify({"logs": []})

# Static files
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    print("🚀 AUDITOS DEMO WEBSITE STARTING...")
    print("🌐 Open: http://localhost:5001")
    print("📸 Upload images to test fraud detection")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5001)