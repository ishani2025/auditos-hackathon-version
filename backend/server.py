# backend/server.py - ADD JUST THESE 3 LINES
from flask import Flask, jsonify
from flask_cors import CORS  # <-- ADD THIS LINE
import os, sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from routes.upload import upload_bp
    uploaded = True
except Exception as e:
    upload_bp = None
    uploaded = False

app = Flask(__name__)
CORS(app)  # <-- ADD THIS LINE (enables Android connections)

if upload_bp:
    app.register_blueprint(upload_bp, url_prefix="/")

@app.route("/")
def home():
    return jsonify({"message":"AuditOS Backend running", "upload_route": "active" if uploaded else "missing"})

@app.route("/test")
def test():
    return jsonify({"ok": True, "upload_route": uploaded})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)