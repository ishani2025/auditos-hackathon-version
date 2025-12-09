# backend/models/dbp.py
"""
DBP: Database for 256-bit pHash Storage and Duplicate Checking
"""

import sqlite3
import logging # <-- NEW: Logging for fraud attempts and errors
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import os
import sys

# Set up logging for reporting fraud/errors
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ========== FIX IMPORTS ==========
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.insert(0, backend_dir)

# --- Define the desired default threshold here for consistency ---
PHASH_DEFAULT_THRESHOLD = 130

try:
    from services.dhash import PhashService 
    phash_service = PhashService() 
    logging.info("✅ Successfully imported 256-bit PhashService")
except ImportError as e:
    logging.warning(f"⚠️ Import Error: {e}")
    
    class MockPhashService:
        @staticmethod
        # Using the centralized constant for the mock service
        def compare_256bit(hash1, hash2, threshold=PHASH_DEFAULT_THRESHOLD): 
            if not hash1 or not hash2:
                return False, 256
            distance = sum(1 for a, b in zip(hash1, hash2) if a != b) * (256 / len(hash1)) if len(hash1) > 0 else 256
            return distance <= threshold, int(distance)
        
        compare = compare_256bit
    
    phash_service = MockPhashService()
    logging.warning("⚠️ Using mock phash_service (256-bit compatible)")
# ========== END FIX ==========

class PhashDatabase:
    """
    Manages storage and retrieval of 256-bit image pHash fingerprints
    """
    
    # NEW: Define the default threshold as a class constant for consistency
    DEFAULT_THRESHOLD = PHASH_DEFAULT_THRESHOLD 
    
    def __init__(self, db_path: str = "auditos_phashes.db"):
        self.db_path = db_path
        self.init_database()
        logging.info(f"✅ 256-bit pHash Database initialized: {db_path}")
    
    def init_database(self):
        """Create the pHash database tables with proper column size for 256-bit"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main table for 256-bit image hashes (64 hex chars)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS image_hashes_256bit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_hash TEXT NOT NULL UNIQUE,  -- 64 hex chars = 256 bits
            credit_id TEXT NOT NULL UNIQUE,
            account_id TEXT NOT NULL,
            image_path TEXT,
            file_size INTEGER,
            timestamp TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Add CHECK constraint to ensure 64-char hashes
        try:
            cursor.execute('''
            ALTER TABLE image_hashes_256bit 
            ADD CHECK (length(image_hash) = 64)
            ''')
        except:
            pass
        
        conn.commit()
        conn.close()
    
    def store_256bit_hash(self, image_hash: str, credit_id: str, account_id: str,
                              image_path: str = None, file_size: int = 0) -> bool:
        """Store a 256-bit pHash in the database"""
        
        # Validate: Must be 64 hex characters
        if not image_hash or len(image_hash) != 64:
            logging.error(f"❌ Invalid 256-bit hash length: {len(image_hash) if image_hash else 0} (expected 64)")
            return False
        
        # Validate: Must be hexadecimal
        try:
            int(image_hash, 16)
        except ValueError:
            logging.error(f"❌ Invalid hex string: {image_hash}")
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
            # Log successful storage
            logging.info(f"💾 Stored 256-bit pHash for credit: {credit_id}. Hash: {image_hash[:8]}... Account: {account_id}")
            return True
            
        except sqlite3.IntegrityError as e:
            # Log Integrity Errors (duplicate credit_id or hash)
            logging.error(f"🚫 Database Integrity Error (Hash/Credit ID collision): {e}. Hash: {image_hash[:8]}...")
            return False
        except Exception as e:
            logging.error(f"❌ Error storing 256-bit hash: {e}")
            return False
        finally:
            conn.close()
    
    def check_duplicate_256bit(self, new_hash: str, account_id: str = None,
                              threshold: int = None) -> Dict:
        """Check if an image is duplicate using 256-bit pHash"""
        
        # Use instance-specific threshold if provided, otherwise use the class default
        if threshold is None:
            threshold = self.DEFAULT_THRESHOLD
            
        # Validate: Must be 64 hex characters
        if not new_hash or len(new_hash) != 64:
            return {
                "error": f"Invalid 256-bit hash length: {len(new_hash)} (expected 64)",
                "is_duplicate": False
            }
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Get all stored 256-bit hashes
            if account_id:
                cursor.execute('''
                SELECT image_hash, credit_id, account_id 
                FROM image_hashes_256bit 
                WHERE account_id = ?
                ''', (account_id,))
            else:
                cursor.execute('SELECT image_hash, credit_id, account_id FROM image_hashes_256bit')
            
            stored_records = cursor.fetchall()
            total_checked = len(stored_records)
            
            logging.info(f"🔍 Checking {new_hash[:8]}... against {total_checked} stored hashes (Threshold: {threshold})")
            
            duplicates_found = []
            
            for record in stored_records:
                stored_hash = record['image_hash']
                stored_credit = record['credit_id']
                
                # Use 256-bit comparison (phash_service.compare_256bit)
                is_similar, distance = phash_service.compare_256bit(new_hash, stored_hash, threshold)
                
                if is_similar:
                    
                    # --- NEW: Logging potential fraud (near-duplicate match) ---
                    logging.warning(f"🚫 Potential Fraud Detected (Distance: {distance}). New Hash: {new_hash[:8]}... matches Credit: {stored_credit}")
                    
                    duplicates_found.append({
                        "credit_id": stored_credit,
                        "hash": stored_hash,
                        "distance": distance,
                        "account": record['account_id']
                    })
            
            if duplicates_found:
                closest = min(duplicates_found, key=lambda x: x["distance"])
                
                print(f"🚫 FOUND {len(duplicates_found)} 256-BIT DUPLICATES!")
                for dup in duplicates_found[:3]:
                    print(f"   • Credit: {dup['credit_id']}, Distance: {dup['distance']}")
                
                return {
                    "is_duplicate": True,
                    "total_checked": total_checked,
                    "duplicates_found": len(duplicates_found),
                    "closest_match": closest,
                    "all_matches": duplicates_found
                }
            else:
                logging.info(f"✅ No 256-bit duplicates found for {new_hash[:8]}...")
                return {
                    "is_duplicate": False,
                    "total_checked": total_checked,
                    "duplicates_found": 0
                }
                
        except Exception as e:
            logging.error(f"❌ Fatal Error checking 256-bit duplicates: {e}")
            return {
                "is_duplicate": False,
                "error": str(e),
                "total_checked": 0
            }
        finally:
            conn.close()
    
    store_hash = store_256bit_hash
    check_duplicate = check_duplicate_256bit

# Create global instance
phash_db = PhashDatabase()