# Flask app setup and routing# backend/server.py
from flask import Flask, jsonify, request
import os

# Create Flask app
app = Flask(__name__)

# Route 1: Home page - check if server is running
@app.route('/')
def home():
    return jsonify({
        "message": "AuditOS Backend is running!",
        "status": "ok",
        "endpoints": {
            "GET /": "This page",
            "GET /health": "Health check",
            "POST /upload": "Upload image (demo)",
            "GET /test": "Test endpoint"
        }
    })

# Route 2: Health check
@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

# Route 3: Test upload (simplest version)
@app.route('/upload', methods=['POST'])
def upload():
    """
    Simple upload endpoint
    Expects: JSON with image data (we'll make it simple)
    """
    try:
        # Get data from request (for now, just text)
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "No data received",
                "tip": "Send JSON with 'image_name' field"
            }), 400
        
        # Simple response
        return jsonify({
            "status": "success",
            "message": "Image received! (demo mode)",
            "received_data": data,
            "credit_id": "DEMO_001",
            "fraud_detected": False
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route 4: Test endpoint (GET request)
@app.route('/test')
def test():
    return jsonify({
        "message": "Backend is working!",
        "next_step": "Send POST request to /upload with JSON",
        "example": {
            "image_name": "trash_pile.jpg",
            "latitude": 12.9716,
            "longitude": 77.5946
        }
    })

# Run the server
if __name__ == '__main__':
    port = 5000
    print("=" * 50)
    print("🚀 Starting AuditOS Backend...")
    print(f"📡 Server will run at: http://localhost:{port}")
    print("=" * 50)
    print("\n📝 Try these URLs in your browser:")
    print(f"1. http://localhost:{port}/")
    print(f"2. http://localhost:{port}/health")
    print(f"3. http://localhost:{port}/test")
    print("\n⚡ To test upload endpoint, use the test.py script")
    print("=" * 50)
    
    app.run(debug=True, port=port)