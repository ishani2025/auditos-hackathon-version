# backend/models/dbp.py
"""
DBP: Database for 256-bit pHash Storage and Duplicate Checking
"""

import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import os
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ---------------------------------------------------------
# Add backend directory to sys.path so imports always work
# ---------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.insert(0, backend_dir)

# Default threshold for pure pHash comparisons
PHASH_DEFAULT_THRESHOLD = 130   

# ---------------------------------------------------------
# IMPORT PURE PHASH SERVICE SAFELY
# ---------------------------------------------------------
try:
    from services.phash import phash_service
    logging.info("✅ Successfully imported PurePhashService")
except Exception as e:
    logging.warning(f"⚠️ PurePhashService import failed: {e}")

    class MockPhashService:
        """Fallback for development only."""
        def compare(self, hash1: str, hash2: str, threshold: int = PHASH_DEFAULT_THRESHOLD):
            if not hash1 or not hash2:
                return False, 9999
            min_len = min(len(hash1), len(hash2))
            dist = sum(a != b for a, b in zip(hash1[:min_len], hash2[:min_len]))
            return dist <= threshold, dist

    phash_service = MockPhashService()
    logging.warning("⚠️ Using MockPhashService fallback")


# =========================================================
#                    DATABASE CLASS
# =========================================================

class PhashDatabase:
    """Stores & checks pure perceptual hashes (64 hex chars = 256-bit)."""

    DEFAULT_THRESHOLD = PHASH_DEFAULT_THRESHOLD

    def __init__(self, db_path: str = "auditos_phashes.db"):
        self.db_path = db_path
        self.init_database()
        logging.info(f"✅ pHash database initialized at {db_path}")

    # -----------------------------------------------------
    # CREATE DATABASE TABLE
    # -----------------------------------------------------
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS image_hashes_256bit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_hash TEXT NOT NULL UNIQUE,
            credit_id TEXT NOT NULL UNIQUE,
            account_id TEXT NOT NULL,
            image_path TEXT,
            file_size INTEGER,
            timestamp TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Enforce hex length = 64 (256 bits)
        try:
            cursor.execute(
                "ALTER TABLE image_hashes_256bit "
                "ADD CHECK(length(image_hash) = 64)"
            )
        except Exception:
            pass

        conn.commit()
        conn.close()

    # -----------------------------------------------------
    # STORE HASH
    # -----------------------------------------------------
    def store_256bit_hash(self, image_hash: str, credit_id: str, account_id: str,
                          image_path: str = None, file_size: int = 0) -> bool:

        if not image_hash or len(image_hash) != 64:
            logging.error(f"❌ Invalid hash length {len(image_hash)} (expected 64)")
            return False

        # Validate hex
        try:
            int(image_hash, 16)
        except:
            logging.error(f"❌ Invalid hex hash: {image_hash}")
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO image_hashes_256bit
                (image_hash, credit_id, account_id, image_path, file_size, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                image_hash,
                credit_id,
                account_id,
                image_path,
                file_size,
                datetime.utcnow().isoformat()
            ))

            conn.commit()
            logging.info(f"💾 Stored hash for credit {credit_id}: {image_hash[:12]}...")
            return True

        except sqlite3.IntegrityError as e:
            logging.error(f"🚫 Duplicate hash or credit_id: {e}")
            return False

        except Exception as e:
            logging.error(f"❌ DB Insert Error: {e}")
            return False

        finally:
            conn.close()

    store_hash = store_256bit_hash  # alias

    # -----------------------------------------------------
    # CHECK DUPLICATES
    # -----------------------------------------------------
    def check_duplicate_256bit(self, new_hash: str, account_id: str = None,
                               threshold: int = None) -> Dict:

        if threshold is None:
            threshold = self.DEFAULT_THRESHOLD

        if not new_hash or len(new_hash) != 64:
            return {"error": "Invalid hash length", "is_duplicate": False}

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Load stored hashes
            if account_id:
                cursor.execute('''
                    SELECT image_hash, credit_id, account_id 
                    FROM image_hashes_256bit WHERE account_id = ?
                ''', (account_id,))
            else:
                cursor.execute('SELECT image_hash, credit_id, account_id FROM image_hashes_256bit')

            records = cursor.fetchall()
            total_checked = len(records)

            duplicates = []

            logging.info(f"🔍 Checking hash {new_hash[:12]}... against {total_checked} stored hashes")

            for row in records:
                stored_hash = row["image_hash"]
                stored_hash_raw = row["image_hash"]

                # --- FIXED: normalize both to 64 hex chars ---
                stored_hash = stored_hash_raw.lower().zfill(64)[:64]
                new_hash_norm = new_hash.lower().zfill(64)[:64]

                stored_credit = row["credit_id"]

                is_similar, distance = phash_service.compare(new_hash_norm, stored_hash, threshold)

                if is_similar:
                    logging.warning(
                        f"🚨 Duplicate Detected! Distance={distance}, credit={stored_credit}"
                    )

                    duplicates.append({
                        "credit_id": stored_credit,
                        "hash": stored_hash,
                        "distance": distance,
                        "account": row["account_id"]
                    })

            if duplicates:
                closest = min(duplicates, key=lambda x: x["distance"])
                return {
                    "is_duplicate": True,
                    "total_checked": total_checked,
                    "duplicates_found": len(duplicates),
                    "closest_match": closest,
                    "all_matches": duplicates
                }

            return {
                "is_duplicate": False,
                "total_checked": total_checked,
                "duplicates_found": 0
            }

        except Exception as e:
            logging.error(f"❌ Duplicate Check Error: {e}")
            return {"is_duplicate": False, "error": str(e), "total_checked": 0}

        finally:
            conn.close()

    check_duplicate = check_duplicate_256bit


# Global DB instance
phash_db = PhashDatabase()
