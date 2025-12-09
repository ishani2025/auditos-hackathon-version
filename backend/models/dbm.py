import sqlite3
import json
import datetime
from typing import Dict, Any, List

class FraudDB:
    """
    Simple SQLite wrapper to persist fraud detection logs.
    Auto-creates the 'screen_logs' table if it doesn't exist.
    """
    
    def __init__(self, db_path="audit_os_logs.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Creates the logging table if missing."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS screen_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    image_hash TEXT,
                    score REAL,
                    fft_score REAL,
                    fraud_detected BOOLEAN,
                    reason TEXT,
                    ip_address TEXT,
                    device_info TEXT
                )
            """)
            conn.commit()

    def log_screen_fraud(self, payload: Dict[str, Any]):
        """
        Logs a detection result to the database.
        
        Expected payload keys:
        - image_hash, edge_score, threshold, fraud_detected, reason, ip_address, device_info
        """
        # Convert dict/list fields to JSON strings for SQLite storage
        device_info_str = json.dumps(payload.get("device_info", {}))
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO screen_logs (
                    image_hash,score, fft_score, fraud_detected, 
                    reason, ip_address,device_info
                ) VALUES (?, ?, ?, ?, ?, ?,?)
            """, (
                payload.get("image_hash", "unknown"),
                payload.get("score", 0.0),
                payload.get("fft_score", 0.0),
                payload.get("fraud_detected", False),
                payload.get("reason", ""),
                payload.get("ip_address", ""),
                device_info_str
            ))
            conn.commit()

    def get_recent_logs(self, limit: int = 5) -> List[tuple]:
        """Returns the N most recent logs."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, timestamp, fraud_detected, reason, edge_score 
                FROM screen_logs 
                ORDER BY id DESC 
                LIMIT ?
            """, (limit,))
            return cursor.fetchall()

# Global instance to be imported by other modules
fraud_db = FraudDB()