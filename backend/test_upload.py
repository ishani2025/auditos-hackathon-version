# backend/test_upload.py - SIMPLE WORKING VERSION
"""
Run with: python test_upload.py
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Flask
from flask import Flask

try:
    # Try to import upload_bp
    from routes.upload import upload_bp
    print("✅ Imported upload_bp from routes.upload")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("\nCreating a test blueprint...")
    
    # Create test blueprint
    from flask import Blueprint, jsonify
    upload_bp = Blueprint('upload', __name__)
    
    @upload_bp.route('/test')
    def test():
        return jsonify({'status': 'test', 'message': 'Test blueprint'})
    
    @upload_bp.route('/upload', methods=['POST'])
    def upload():
        return jsonify({'status': 'test', 'message': 'Test upload endpoint'})

# Create app
app = Flask(__name__)
app.register_blueprint(upload_bp, url_prefix='/api')

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Server starting at http://localhost:5000")
    print("="*60)
    app.run(debug=True, port=5000, host='0.0.0.0')