# website/run.py
"""
Simple runner for the AuditOS demo website
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("🚀 Starting AuditOS Demo Website...")
print("=" * 50)
print("📂 Folder structure:")
print("  website/")
print("  ├── app.py              # Flask web app")
print("  ├── templates/index.html # Web interface")
print("  ├── static/uploads/     # Uploaded images")
print("  └── static/images/      # Reference images")
print()
print("🌐 Website will run at: http://localhost:5001")
print("📸 Upload images to test fraud detection")
print("=" * 50)

# Run the app
from website.app import app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)