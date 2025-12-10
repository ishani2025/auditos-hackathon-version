# auditos
**AuditOS** is a forensic waste-verification engine that validates EPR credits using real-world camera evidence, geolocation checks, duplicate detection, screen-fraud rejection, and randomized liveness challenges. It ensures only authentic waste disposal earns credits, preventing fraud in recycling compliance.
# 🗑️ AuditOS – Forensic Waste Credit Verification Engine

AuditOS is a rule-driven fraud detection system that authenticates real-world waste disposal evidence before issuing Extended Producer Responsibility (EPR) credits. Built for the GLYTCH Hackathon, it demonstrates a complete verification pipeline that can later evolve into a hardened Android edge client.

---

## 🔍 Problem

Most EPR credit systems rely on manual proofs (photos, invoices, GPS notes), which are easy to fake. Credits can be fraudulently generated using:
- Duplicate images of the same waste
- Screenshots or photos of screens
- Verification of Location
- Photos taken from the internet
- Reused media across different locations

This leads to inflated recycling credits, loss of compliance funds, and unreliable environmental reporting.

---

## 🛡️ Solution — AuditOS

AuditOS enforces **verifiable waste provenance** using:

| Capability | Details |
|------------|---------|
| 📸 **Camera Evidence** | Captured directly from device webcam/mobile |
| 🖥️ **Screen Fraud Rejection** | OpenCV border-edge forensic filter |
| 🔁 **Duplicate Waste Detection** | Perceptual Hashing (pHash) + Hamming distance |
| 📍 **Geo-Fence Validation** | Rejects claims outside operational area |
| 🎲 **Randomized Challenges** | Prompts to prove liveness (tilt, move closer, etc.) |
| ✋ **Digging Challenge** | Requires a second capture from a changed angle |

Only proofs that pass all checks are marked **APPROVED** and eligible for credit generation.

---

## 🏗️ Tech Stack

### 🔧 Backend
- Python + Flask
- Pillow (image handling)
- ImageHash (pHash, similarity)
- OpenCV (screen detection)
- SQLite (audit trails)

### 🌐 Frontend (Hackathon Prototype)
- Android Studio

### 🚀 Roadmap (Post-Hackathon)
| Phase | Upgrade |
|-------|---------|
| Edge Client | Android App with secure inference |
| ML Stage 1 | Screen forensics using Moiré + glare detection |
| ML Stage 2 | Material classification + volume estimation |
| ML Stage 3 | Anti-spoof liveness camera model |

---

## 🧪 Demo Workflow

1. Capture base waste image using webcam/mobile.
2. Backend issues a **random challenge** (e.g., tilt left).
3. Capture challenge image from a new angle.
4. Backend verifies:
   - **Not a screen**
   - **Not a duplicate**
   - **Within geo-fence**
   - **Challenge completed**
5. `/submissions` shows full audit log with flags.

---

## 📌 API Overview

### `POST /verify`
Accepts:
- `image_main`
- `image_challenge`
- `lat`, `lng`
- `challenge_id`

Returns JSON:

```json
{
  "status": "APPROVED | DUPLICATE | REJECTED | FLAGGED",
  "screen_suspected": false,
  "duplicate": false,
  "geo_suspicious": false,
  "challenge_completed": true,
  "similarity_score": 0.14,
  "message": "Credit approved"
}
GET /challenge
Returns a random liveness instruction:

{
  "challenge_id": "MOVE_CLOSER",
  "challenge_text": "Move the camera closer and capture again."
}
📊 Audit Dashboard
GET /submissions
Lists all captured attempts with:

status

similarity score

geo flags

challenge type

timestamp

🧱 Local Setup
git clone <repo-link>
cd auditos-hack/backend
python -m venv venv
source venv/bin/activate   # or .\venv\Scripts\activate
pip install -r requirements.txt
python app.py
Then open:
http://127.0.0.1:5000/

🤝 Contributors
Developed by AuditOS Contributors during the GLYTCH Hackathon, 2025.
Open for collaboration and research contributions post-hackathon.

🌍 Impact Vision
AuditOS enforces provable recycling compliance by ensuring that every claimed credit corresponds to traceable, genuine waste. With explainable fraud controls before AI integration, it enables transparent, scalable and trustworthy circular-economy reporting.
