# backend/models/dbp.py
"""
DBP: Database for 256-bit pHash Storage and Duplicate Checking
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import os
import sys

# ========== FIX IMPORTS ==========
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.insert(0, backend_dir)

try:
    from services.phash import PhashService 
    phash_service = PhashService() # This instance is 256-bit by default now
    print("✅ Successfully imported 256-bit PhashService")
except ImportError as e:
    # Mock service for 256-bit functionality
    print(f"⚠️ Import Error: {e}")
    
    class MockPhashService:
        @staticmethod
        # THRESHOLD IS 130 HERE FOR CONSISTENCY
        def compare_256bit(hash1, hash2, threshold=130): 
            if not hash1 or not hash2:
                return False, 256
            distance = sum(1 for a, b in zip(hash1, hash2) if a != b) * (256 / len(hash1)) if len(hash1) > 0 else 256
            return distance <= threshold, int(distance)
        
        compare = compare_256bit
    
    phash_service = MockPhashService()
    print("⚠️ Using mock phash_service (256-bit compatible)")
# ========== END FIX ==========

class PhashDatabase:
    """
    Manages storage and retrieval of 256-bit image pHash fingerprints
    """
    
    def __init__(self, db_path: str = "auditos_phashes.db"):
        self.db_path = db_path
        self.init_database()
        print(f"✅ 256-bit pHash Database initialized: {db_path}")
    
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
            print(f"❌ Invalid 256-bit hash length: {len(image_hash) if image_hash else 0} (expected 64)")
            return False
        
        # Validate: Must be hexadecimal
        try:
            int(image_hash, 16)
        except ValueError:
            print(f"❌ Invalid hex string: {image_hash}")
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
            print(f"💾 Stored 256-bit pHash for credit: {credit_id}")
            print(f"   Hash: {image_hash}")
            print(f"   Account: {account_id}")
            return True
            
        except sqlite3.IntegrityError as e:
            print(f"🚫 Database integrity error: {e}")
            return False
        except Exception as e:
            print(f"❌ Error storing 256-bit hash: {e}")
            return False
        finally:
            conn.close()
    
    def check_duplicate_256bit(self, new_hash: str, account_id: str = None,
                              threshold: int = 130) -> Dict: # <--- FIX: THRESHOLD CHANGED TO 130
        """Check if an image is duplicate using 256-bit pHash"""
        
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
            
            print(f"🔍 Checking against {total_checked} stored 256-bit hashes")
            
            duplicates_found = []
            
            for record in stored_records:
                stored_hash = record['image_hash']
                stored_credit = record['credit_id']
                
                # Use 256-bit comparison (phash_service.compare_256bit)
                is_similar, distance = phash_service.compare_256bit(new_hash, stored_hash, threshold)
                
                if is_similar:
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
                print(f"✅ No 256-bit duplicates found (checked {total_checked} images)")
                return {
                    "is_duplicate": False,
                    "total_checked": total_checked,
                    "duplicates_found": 0
                }
                
        except Exception as e:
            print(f"❌ Error checking 256-bit duplicates: {e}")
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