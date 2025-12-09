# backend/routes/upload.py
"""
GlitchOps AuditOS - Image Upload Route
Calls external services (phash.py, detect_screen.py)
"""

import os
import sys
import uuid
import hashlib
from datetime import datetime

# ====================
# FIX: ADD PARENT DIRECTORY TO PATH
# ====================
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)  # Go up to backend/
sys.path.insert(0, backend_dir)  # Add backend to Python path

# Now import Flask
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

# ====================
# 1. CREATE BLUEPRINT
# ====================
upload_bp = Blueprint('upload', __name__)

# ====================
# 2. CONFIGURATION
# ====================
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

# Create upload directory
UPLOAD_DIR = os.path.join(backend_dir, 'temp_uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ====================
# 3. IMPORT EXTERNAL SERVICES
# ====================
print("\n🔧 Loading external services...")

# Try to import screen detection service - UPDATED FOR YOUR CODE
try:
    # Your detect_screen.py has ScreenFraudDetector class, not detect_screen_fraud function
    from services.detect_screen import ScreenFraudDetector
    
    # Create the function that matches what your code expects
    def detect_screen_fraud(image_path):
        """
        Wrapper function that matches your original detect_screen_fraud signature
        Uses your ScreenFraudDetector class
        """
        # Use your tuned thresholds from detect_screen.py
        detector = ScreenFraudDetector(blur_threshold=50.0, fft_threshold=15.0)
        result = detector.detect(image_path)
        
        # Calculate confidence based on laplacian score
        # Your original formula: 100 - min(100, max(0, result.get('score', 0) / 10))
        laplacian_score = result.get('score', 0)
        confidence = 100 - min(100, max(0, laplacian_score / 10))
        
        return {
            'is_screen': result['fraud_detected'],
            'confidence': confidence,
            'reasons': [result['reason']] if result['reason'] else [],
            'details': {
                'laplacian_score': laplacian_score,
                'fft_score': result.get('fft_score', 0),
                'image_hash': result.get('image_hash', '')
            }
        }
    
    SCREEN_DETECTION_AVAILABLE = True
    print("✅ Screen detection service loaded (using ScreenFraudDetector class)")
except ImportError as e:
    print(f"⚠️  Could not import screen detection service: {e}")
    print(f"⚠️  Looking in: {os.path.join(backend_dir, 'services')}")
    SCREEN_DETECTION_AVAILABLE = False

# Try to import pHash service
try:
    from services.phash import phash_service
    FINGERPRINTER_AVAILABLE = True
    print("✅ pHash service loaded")
except ImportError as e:
    print(f"⚠️  Could not import pHash service: {e}")
    FINGERPRINTER_AVAILABLE = False

# ====================
# 4. HELPER FUNCTIONS
# ====================
def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_temp_file(file):
    """Save uploaded file to temporary location"""
    # Generate unique filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    unique_id = uuid.uuid4().hex[:8]
    original_name = secure_filename(file.filename)
    
    filename = f"{timestamp}_{unique_id}_{original_name}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    file.save(filepath)
    print(f"📁 Saved temp file: {filename} ({os.path.getsize(filepath)} bytes)")
    
    return filepath, filename

def generate_simple_hash(image_path):
    """Fallback hash function"""
    with open(image_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()[:16]

def generate_credit_id(device_id):
    """Generate unique credit ID"""
    timestamp = datetime.now().strftime('%Y%m%d')
    unique_id = uuid.uuid4().hex[:8].upper()
    return f"EPR-{timestamp}-{unique_id}"

def cleanup_file(filepath):
    """Clean up temporary file"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"🧹 Cleaned up: {os.path.basename(filepath)}")
    except Exception as e:
        print(f"⚠️ Could not clean up file: {e}")

# ====================
# 5. DUPLICATE DATABASE
# ====================
class SimpleDuplicateDB:
    """Simple in-memory database"""
    def __init__(self):
        self.hashes = {}  # hash -> credit_id
        print("📊 Initialized duplicate database")
    
    def check_duplicate(self, image_hash, threshold=35):
        """Check if hash is similar to any stored"""
        duplicates = []
        
        for stored_hash, credit_id in self.hashes.items():
            if FINGERPRINTER_AVAILABLE:
                is_similar, distance = phash_service.compare(image_hash, stored_hash, threshold)
            else:
                # Simple comparison for fallback
                distance = sum(1 for a, b in zip(image_hash, stored_hash) if a != b)
                is_similar = distance <= 8  # Adjust for MD5
            
            if is_similar:
                duplicates.append({
                    'credit_id': credit_id,
                    'distance': distance,
                    'similarity': f"{(256 - distance)/256*100:.1f}%" if FINGERPRINTER_AVAILABLE else f"{(16 - distance)/16*100:.1f}%"
                })
        
        return {
            'is_duplicate': len(duplicates) > 0,
            'duplicates_found': len(duplicates),
            'matches': duplicates
        }
    
    def store_hash(self, image_hash, credit_id):
        """Store hash in memory"""
        self.hashes[image_hash] = credit_id
        return True

# Create global instance
duplicate_db = SimpleDuplicateDB()

# ====================
# 6. MAIN UPLOAD ROUTE
# ====================
@upload_bp.route('/upload', methods=['POST'])
def upload_image():
    """
    Main endpoint for image upload
    Uses external services for detection
    """
    print("\n" + "="*60)
    print("📸 NEW UPLOAD REQUEST RECEIVED")
    print("="*60)
    
    # Validate request
    if 'image' not in request.files:
        return jsonify({'status': 'error', 'message': 'No image file'}), 400
    
    file = request.files['image']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'status': 'error', 'message': 'Invalid file'}), 400
    
    # Get metadata
    device_id = request.form.get('device_id', 'unknown_device')
    latitude = request.form.get('latitude', '0.0')
    longitude = request.form.get('longitude', '0.0')
    timestamp = request.form.get('timestamp', datetime.utcnow().isoformat())
    
    print(f"📱 Device: {device_id}")
    print(f"📍 Location: {latitude}, {longitude}")
    print(f"🕒 Time: {timestamp}")
    
    # Save temp file
    try:
        temp_path, temp_filename = save_temp_file(file)
        file_size = os.path.getsize(temp_path)
        print(f"📏 File: {temp_filename} ({file_size:,} bytes)")
    except Exception as e:
        print(f"❌ Error saving file: {e}")
        return jsonify({'status': 'error', 'message': f'Could not save file: {str(e)}'}), 500
    
    try:
        # Step 1: Screen fraud detection (external service)
        screen_check = None
        if SCREEN_DETECTION_AVAILABLE:
            print("\n🔍 Calling screen detection service...")
            screen_check = detect_screen_fraud(temp_path)
            
            if screen_check['is_screen']:
                print(f"🚨 REAL SCREEN FRAUD DETECTED!")
                print(f"   Confidence: {screen_check['confidence']}%")
                print(f"   Reason: {screen_check['reasons'][0] if screen_check['reasons'] else 'Unknown'}")
                print(f"   Laplacian Score: {screen_check['details'].get('laplacian_score', 0):.2f}")
                print(f"   FFT Score: {screen_check['details'].get('fft_score', 0):.2f}")
                
                cleanup_file(temp_path)
                
                return jsonify({
                    'status': 'fraud',
                    'fraud_type': 'screen_photo',
                    'confidence': screen_check['confidence'],
                    'reasons': screen_check['reasons'],
                    'technical_details': screen_check['details'],
                    'message': 'Image appears to be a photo of a screen (REAL DETECTION)'
                }), 400
            
            print(f"✅ Screen check passed (REAL DETECTION)")
            print(f"   Laplacian: {screen_check['details'].get('laplacian_score', 0):.2f}")
            print(f"   FFT: {screen_check['details'].get('fft_score', 0):.2f}")
        else:
            print("⚠️  Screen detection not available (missing OpenCV or services)")
        
        # Step 2: Generate fingerprint (external service)
        if FINGERPRINTER_AVAILABLE:
            print("\n👆 Calling pHash service...")
            image_hash, _ = phash_service.create_fingerprint(temp_path)
            print(f"✅ 256-bit pHash generated: {image_hash[:32]}...")
            print(f"   Hash length: {len(image_hash)} characters")
        else:
            image_hash = generate_simple_hash(temp_path)
            print(f"⚠️  Using simple MD5 hash (fallback): {image_hash}")
        
        # Step 3: Check duplicates
        print("\n🔎 Checking for duplicate images...")
        threshold = 35 if FINGERPRINTER_AVAILABLE else 8
        duplicate_check = duplicate_db.check_duplicate(image_hash, threshold=threshold)
        
        if duplicate_check['is_duplicate']:
            print(f"🚨 DUPLICATE FOUND! ({duplicate_check['duplicates_found']} matches)")
            
            for match in duplicate_check['matches'][:3]:
                print(f"   • Similar to credit {match['credit_id']} ({match['similarity']}, distance: {match['distance']})")
            
            cleanup_file(temp_path)
            
            return jsonify({
                'status': 'fraud',
                'fraud_type': 'duplicate_image',
                'matches': duplicate_check['matches'],
                'hash_used': '256-bit pHash' if FINGERPRINTER_AVAILABLE else 'MD5 hash',
                'threshold_used': threshold,
                'message': 'Similar image already exists in system'
            }), 400
        
        print(f"✅ No duplicates found (checked {len(duplicate_db.hashes)} images)")
        
        # Step 4: Generate credit
        credit_id = generate_credit_id(device_id)
        
        # Calculate credit amount based on file size (demo logic)
        base_amount = 5.0
        size_bonus = min(file_size / (1024 * 1024), 50)
        credit_amount = round(base_amount + size_bonus, 2)
        
        print(f"\n💰 CREDIT GENERATED:")
        print(f"   Credit ID: {credit_id}")
        print(f"   Amount: ${credit_amount}")
        
        # Step 5: Store in database
        print("\n💾 Storing in database...")
        duplicate_db.store_hash(image_hash, credit_id)
        
        # Step 6: Prepare response
        response_data = {
            'status': 'verified',
            'credit_id': credit_id,
            'credit_amount': credit_amount,
            'image_hash': image_hash,
            'hash_type': '256-bit pHash' if FINGERPRINTER_AVAILABLE else 'MD5 (fallback)',
            'verification_timestamp': datetime.utcnow().isoformat(),
            'fraud_checks': {
                'screen_detection': {
                    'passed': True,
                    'available': SCREEN_DETECTION_AVAILABLE,
                    'confidence': screen_check['confidence'] if SCREEN_DETECTION_AVAILABLE and screen_check else 0
                },
                'duplicate_check': {
                    'passed': True,
                    'available': FINGERPRINTER_AVAILABLE,
                    'images_checked': len(duplicate_db.hashes),
                    'threshold_used': threshold
                }
            },
            'metadata': {
                'device_id': device_id,
                'location': {
                    'latitude': latitude,
                    'longitude': longitude
                },
                'file_info': {
                    'original_name': file.filename,
                    'size_bytes': file_size,
                    'size_mb': round(file_size / (1024 * 1024), 2)
                }
            }
        }
        
        # Add screen detection details if available
        if SCREEN_DETECTION_AVAILABLE and screen_check:
            response_data['screen_analysis'] = screen_check['details']
        
        print(f"\n✅ UPLOAD SUCCESSFUL!")
        print(f"   Credit issued: {credit_id}")
        print(f"   Amount: ${credit_amount}")
        print(f"   Hash type: {response_data['hash_type']}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'Internal error: {str(e)}'}), 500
        
    finally:
        cleanup_file(temp_path)
        print("\n🧹 Cleanup completed")
        print("="*60 + "\n")

# ====================
# 7. ADDITIONAL ROUTES
# ====================
@upload_bp.route('/test', methods=['GET'])
def test_endpoint():
    return jsonify({
        'status': 'ok',
        'message': 'Upload route active with modular services',
        'services': {
            'screen_detection': SCREEN_DETECTION_AVAILABLE,
            'pHash': FINGERPRINTER_AVAILABLE
        }
    })

@upload_bp.route('/stats', methods=['GET'])
def get_stats():
    return jsonify({
        'status': 'ok',
        'uploads': len(duplicate_db.hashes),
        'services': {
            'screen_detection': SCREEN_DETECTION_AVAILABLE,
            'pHash': FINGERPRINTER_AVAILABLE
        }
    })

# ====================
# 8. INITIALIZATION
# ====================
print("\n" + "="*60)
print("🚀 MODULAR UPLOAD ROUTE INITIALIZED")
print("="*60)
print(f"📁 Temp directory: {UPLOAD_DIR}")
print(f"📄 Allowed extensions: {ALLOWED_EXTENSIONS}")
print(f"🔍 Screen detection: {'✅ Available' if SCREEN_DETECTION_AVAILABLE else '❌ Not available'}")
print(f"👆 pHash service: {'✅ Available' if FINGERPRINTER_AVAILABLE else '❌ Not available'}")
print("="*60)

if __name__ == '__main__':
    print("✅ Upload module loaded successfully!")