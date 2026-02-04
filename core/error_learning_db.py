"""
Error Learning Database - PHASE 1 CRITICAL

Remembers every error, solution, and outcome to prevent recurrence.
"""
import sqlite3
import json
import hashlib
from datetime import datetime
from typing import Optional, Dict, List

class ErrorLearningDatabase:
    def __init__(self, db_path: str = "error_learning.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS errors (
                id INTEGER PRIMARY KEY,
                error_signature TEXT UNIQUE,
                error_type TEXT,
                error_message TEXT,
                first_seen TEXT,
                last_seen TEXT,
                occurrence_count INTEGER DEFAULT 1,
                solution TEXT,
                success_rate REAL DEFAULT 0.0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS solutions (
                id INTEGER PRIMARY KEY,
                error_signature TEXT,
                solution_type TEXT,
                solution_code TEXT,
                applied_at TEXT,
                success INTEGER,
                execution_time_ms REAL,
                FOREIGN KEY (error_signature) REFERENCES errors(error_signature)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def remember_error(self, error: Exception, solution: str, success: bool):
        """Remember an error and its solution"""
        signature = self._get_signature(error)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Upsert error
        cursor.execute('''
            INSERT INTO errors (error_signature, error_type, error_message, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(error_signature) DO UPDATE SET
                occurrence_count = occurrence_count + 1,
                last_seen = ?
        ''', (signature, type(error).__name__, str(error), datetime.now().isoformat(),
              datetime.now().isoformat(), datetime.now().isoformat()))
        
        # Record solution attempt
        cursor.execute('''
            INSERT INTO solutions (error_signature, solution_type, solution_code, applied_at, success)
            VALUES (?, ?, ?, ?, ?)
        ''', (signature, 'auto_fix', solution, datetime.now().isoformat(), 1 if success else 0))
        
        # Update success rate
        cursor.execute('''
            UPDATE errors SET success_rate = (
                SELECT CAST(SUM(success) AS REAL) / COUNT(*) 
                FROM solutions 
                WHERE error_signature = ?
            ) WHERE error_signature = ?
        ''', (signature, signature))
        
        conn.commit()
        conn.close()
    
    def get_known_solution(self, error: Exception) -> Optional[str]:
        """Get best known solution for this error"""
        signature = self._get_signature(error)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT solution FROM errors WHERE error_signature = ?
        ''', (signature,))
        
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else None
    
    def _get_signature(self, error: Exception) -> str:
        """Generate unique signature for error"""
        error_str = f"{type(error).__name__}:{str(error)[:100]}"
        return hashlib.md5(error_str.encode()).hexdigest()[:16]
    
    def get_stats(self) -> Dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*), AVG(success_rate) FROM errors')
        stats = cursor.fetchone()
        
        conn.close()
        
        return {
            'total_errors': stats[0],
            'avg_success_rate': stats[1] or 0
        }
