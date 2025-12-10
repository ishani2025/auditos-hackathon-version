# backend/website/app.py
from flask import Flask, render_template, jsonify, send_from_directory
import os, sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from backend.routes.upload import upload_bp

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "website", "templates"))
app.register_blueprint(upload_bp, url_prefix="/")

# static folders (served by Flask as /static/...)
UPLOAD_FOLDER = os.path.join(BASE_DIR, "website", "static", "uploads")
IMAGES_FOLDER = os.path.join(BASE_DIR, "website", "static", "images")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGES_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["IMAGES_FOLDER"] = IMAGES_FOLDER

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/uploads")
def list_uploads():
    files = []
    for fname in sorted(os.listdir(UPLOAD_FOLDER), key=lambda n: os.path.getmtime(os.path.join(UPLOAD_FOLDER,n)), reverse=True):
        if fname.lower().endswith(('.png','.jpg','.jpeg','.gif','.bmp','.webp')):
            p = os.path.join(UPLOAD_FOLDER, fname)
            files.append({
                "name": fname,
                "url": f"/static/uploads/{fname}",
                "size": os.path.getsize(p)
            })
    return jsonify({"uploads": files})

@app.route("/database")
def list_images():
    files = []
    for fname in sorted(os.listdir(IMAGES_FOLDER), key=lambda n: os.path.getmtime(os.path.join(IMAGES_FOLDER,n)), reverse=True):
        if fname.lower().endswith(('.png','.jpg','.jpeg','.gif','.bmp','.webp')):
            p = os.path.join(IMAGES_FOLDER, fname)
            files.append({
                "name": fname,
                "url": f"/static/images/{fname}",
                "size": os.path.getsize(p)
            })
    return jsonify({"database": files})

# static served automatically by Flask when using send_from_directory via /static/<path>
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(os.path.join(BASE_DIR, "website", "static"), filename)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
