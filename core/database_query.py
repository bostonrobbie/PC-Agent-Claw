#!/usr/bin/env python3
"""Database Query Interface (#92) - Natural language to SQL"""
import sqlite3
from typing import List, Dict

class DatabaseQuery:
    def __init__(self, db_path: str):
        self.db_path = db_path
   
    def query(self, natural_language: str) -> List[Dict]:
        """Convert natural language to SQL and execute"""
        # Simplified - would use LLM in production
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
       
        # Simple keyword mapping
        if 'all tasks' in natural_language.lower():
            cursor.execute('SELECT * FROM tasks')
        elif 'completed tasks' in natural_language.lower():
            cursor.execute("SELECT * FROM tasks WHERE status='completed'")
        elif 'recent decisions' in natural_language.lower():
            cursor.execute('SELECT * FROM decisions ORDER BY created_at DESC LIMIT 10')
        else:
            cursor.execute('SELECT * FROM tasks LIMIT 10')
       
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

if __name__ == '__main__':
    print('Database Query Interface ready')
