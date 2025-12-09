# backend/models/dbp.py
"""
DBP: Database for pHash Storage and Duplicate Checking
This is YOUR database model for image fingerprints
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import hashlib
import os
import sys

# ========== FIX IMPORTS ==========
# Add the backend directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))  # models folder
backend_dir = os.path.dirname(current_dir)  # backend folder
sys.path.insert(0, backend_dir)

try:
    from services.phash import phash_service
    print("✅ Successfully imported phash_service from services")
except ImportError as e:
    print(f"⚠️  Import Error: {e}")
    print("⚠️  Trying alternative import path...")
    
    # Try alternative path
    sys.path.insert(0, os.path.dirname(backend_dir))  # Project root
    
    try:
        from backend.services.phash import phash_service
        print("✅ Successfully imported phash_service from backend.services")
    except ImportError as e2:
        print(f"❌ Could not import phash_service: {e2}")
        print("⚠️  Creating mock service for testing...")
        
        # Create a simple mock for testing
        class MockPhashService:
            @staticmethod
            def compare(hash1, hash2, threshold=10):
                if not hash1 or not hash2:
                    return False, 64
                
                # Simple Hamming distance for hex strings
                distance = sum(1 for a, b in zip(hash1, hash2) if a != b)
                return distance <= threshold, distance
        
        phash_service = MockPhashService()
# ========== END FIX ==========

class PhashDatabase:
    """
    Manages storage and retrieval of image pHash fingerprints
    Works with Ishani's main database (dbm.py)
    """
    
    def __init__(self, db_path: str = "auditos_phashes.db"):
        """
        Initialize pHash database
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.init_database()
        print(f"✅ pHash Database initialized: {db_path}")
    
    def init_database(self):
        """Create the pHash database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main table for image hashes
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS image_hashes (
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
        
        # Table for hash comparisons (for analytics)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS hash_comparisons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            new_hash TEXT NOT NULL,
            existing_hash TEXT NOT NULL,
            hamming_distance INTEGER NOT NULL,
            is_duplicate BOOLEAN NOT NULL,
            threshold_used INTEGER NOT NULL,
            account_id TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Indexes for fast searching
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_hash ON image_hashes(image_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_account ON image_hashes(account_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_credit ON image_hashes(credit_id)')
        
        conn.commit()
        conn.close()
    
    def store_hash(self, image_hash: str, credit_id: str, account_id: str,
                  image_path: str = None, file_size: int = 0) -> bool:
        """
        Store an image hash in the database
        
        Args:
            image_hash: 16-character pHash string
            credit_id: Unique credit identifier
            account_id: Company/account ID
            image_path: Optional path to original image
            file_size: Size of image in bytes
            
        Returns:
            True if stored successfully
        """
        if not image_hash or len(image_hash) != 16:
            print(f"❌ Invalid hash length: {len(image_hash) if image_hash else 0}. Expected 16.")
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO image_hashes 
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
            print(f"💾 Stored pHash for credit: {credit_id}")
            print(f"   Hash: {image_hash}")
            print(f"   Account: {account_id}")
            return True
            
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed: image_hashes.image_hash" in str(e):
                print(f"🚫 Hash already exists in database!")
            elif "UNIQUE constraint failed: image_hashes.credit_id" in str(e):
                print(f"🚫 Credit ID already exists!")
            else:
                print(f"❌ Database error: {e}")
            return False
        except Exception as e:
            print(f"❌ Error storing hash: {e}")
            return False
        finally:
            conn.close()
    
    def check_duplicate(self, new_hash: str, account_id: str = None,
                       threshold: int = 10) -> Dict:
        """
        Check if an image is duplicate by comparing with ALL stored hashes
        
        Args:
            new_hash: New image's pHash (16 chars)
            account_id: If provided, only check this account's images
            threshold: Hamming distance threshold (0-64)
            
        Returns:
            dict with duplicate check results
        """
        if not new_hash:
            return {"error": "No hash provided", "is_duplicate": False}
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Get all stored hashes (or only for this account)
            if account_id:
                cursor.execute('''
                SELECT image_hash, credit_id, account_id 
                FROM image_hashes 
                WHERE account_id = ?
                ''', (account_id,))
                account_filtered = True
            else:
                cursor.execute('SELECT image_hash, credit_id, account_id FROM image_hashes')
                account_filtered = False
            
            stored_records = cursor.fetchall()
            total_checked = len(stored_records)
            
            print(f"🔍 Checking against {total_checked} stored images"
                  f"{' (account: ' + account_id + ')' if account_id else ''}")
            
            duplicates_found = []
            
            for record in stored_records:
                stored_hash = record['image_hash']
                stored_credit = record['credit_id']
                
                # Compare hashes using phash_service
                is_similar, distance = phash_service.compare(new_hash, stored_hash, threshold)
                
                # Log this comparison (for analytics)
                try:
                    cursor.execute('''
                    INSERT INTO hash_comparisons 
                    (new_hash, existing_hash, hamming_distance, is_duplicate, threshold_used, account_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (new_hash, stored_hash, distance, is_similar, threshold, account_id))
                except:
                    pass  # Skip if logging fails
                
                if is_similar:
                    duplicates_found.append({
                        "credit_id": stored_credit,
                        "hash": stored_hash,
                        "distance": distance,
                        "account": record['account_id']
                    })
            
            conn.commit()
            
            if duplicates_found:
                # Find closest duplicate (smallest distance)
                closest = min(duplicates_found, key=lambda x: x["distance"])
                
                print(f"🚫 FOUND {len(duplicates_found)} DUPLICATES!")
                for dup in duplicates_found[:3]:  # Show first 3
                    print(f"   • Credit: {dup['credit_id']}, Distance: {dup['distance']}")
                
                return {
                    "is_duplicate": True,
                    "total_checked": total_checked,
                    "duplicates_found": len(duplicates_found),
                    "closest_match": closest,
                    "all_matches": duplicates_found,
                    "account_filtered": account_filtered
                }
            else:
                print(f"✅ No duplicates found (checked {total_checked} images)")
                return {
                    "is_duplicate": False,
                    "total_checked": total_checked,
                    "duplicates_found": 0,
                    "closest_match": None,
                    "account_filtered": account_filtered
                }
                
        except Exception as e:
            print(f"❌ Error checking duplicates: {e}")
            import traceback
            traceback.print_exc()  # Print full error trace
            return {
                "is_duplicate": False,
                "error": str(e),
                "total_checked": 0
            }
        finally:
            conn.close()
    
    def get_account_stats(self, account_id: str) -> Dict:
        """
        Get statistics for an account
        
        Args:
            account_id: Account to get stats for
            
        Returns:
            dict with statistics
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Get basic counts
            cursor.execute('''
            SELECT 
                COUNT(*) as total_images,
                SUM(file_size) as total_size_bytes,
                MIN(timestamp) as first_upload,
                MAX(timestamp) as last_upload
            FROM image_hashes 
            WHERE account_id = ?
            ''', (account_id,))
            
            stats_row = cursor.fetchone()
            if not stats_row:
                return {}
            
            stats = dict(stats_row)
            
            # Get duplicate attempts blocked
            cursor.execute('''
            SELECT COUNT(*) as duplicates_blocked
            FROM hash_comparisons 
            WHERE account_id = ? AND is_duplicate = 1
            ''', (account_id,))
            
            dup_row = cursor.fetchone()
            if dup_row:
                stats['duplicates_blocked'] = dup_row[0]
            
            # Convert file size to MB
            if stats.get('total_size_bytes'):
                stats['total_size_mb'] = round(stats['total_size_bytes'] / (1024 * 1024), 2)
            
            return stats
            
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
            return {}
        finally:
            conn.close()
    
    def get_recent_hashes(self, account_id: str = None, limit: int = 10) -> List[Dict]:
        """Get recent image hashes"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            if account_id:
                cursor.execute('''
                SELECT * FROM image_hashes 
                WHERE account_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                ''', (account_id, limit))
            else:
                cursor.execute('''
                SELECT * FROM image_hashes 
                ORDER BY timestamp DESC
                LIMIT ?
                ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            print(f"❌ Error getting recent hashes: {e}")
            return []
        finally:
            conn.close()
    
    def export_hashes(self, account_id: str = None) -> List[str]:
        """
        Export all hashes (for backup or transfer)
        
        Returns:
            List of hash strings
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if account_id:
                cursor.execute('SELECT image_hash FROM image_hashes WHERE account_id = ?', (account_id,))
            else:
                cursor.execute('SELECT image_hash FROM image_hashes')
            
            return [row[0] for row in cursor.fetchall()]
            
        except Exception as e:
            print(f"❌ Error exporting hashes: {e}")
            return []
        finally:
            conn.close()

# Create global instance
phash_db = PhashDatabase()

# Test function
def test_dbp():
    """Test the pHash database"""
    print("🧪 Testing pHash Database (DBP)...")
    print("=" * 60)
    
    # Initialize
    test_db = PhashDatabase("test_phashes.db")
    
    # Add some test data
    test_hashes = [
        ("a1b2c3d4e5f6a1b2", "CREDIT_001", "company_a"),
        ("a1b2c3d4e5f7a1b3", "CREDIT_002", "company_a"),  # Similar
        ("ff88cc1122334455", "CREDIT_003", "company_b"),  # Different
    ]
    
    for hash_str, credit_id, account_id in test_hashes:
        test_db.store_hash(hash_str, credit_id, account_id)
    
    print("\n🔍 Testing duplicate detection...")
    
    # Test 1: Check similar hash (should be duplicate)
    print("\nTest 1: Checking similar hash (should be duplicate):")
    result1 = test_db.check_duplicate(
        "a1b2c3d4e5f6a1b2",  # Same as first
        "company_a"
    )
    print(f"   Result: {'DUPLICATE' if result1['is_duplicate'] else 'UNIQUE'}")
    print(f"   Matches found: {result1.get('duplicates_found', 0)}")
    
    # Test 2: Check different hash (should pass)
    print("\nTest 2: Checking different hash (should pass):")
    result2 = test_db.check_duplicate(
        "0000111122223333",
        "company_a"
    )
    print(f"   Result: {'DUPLICATE' if result2['is_duplicate'] else 'UNIQUE'}")
    
    # Test 3: Get stats
    print("\nTest 3: Getting account statistics:")
    stats = test_db.get_account_stats("company_a")
    print(f"   Total images: {stats.get('total_images', 0)}")
    print(f"   Duplicates blocked: {stats.get('duplicates_blocked', 0)}")
    
    # Cleanup
    try:
        os.remove("test_phashes.db")
    except:
        pass
    
    print("\n" + "=" * 60)
    print("✅ DBP (pHASH DATABASE) TEST COMPLETED!")
    print("=" * 60)

if __name__ == "__main__":
    test_dbp()