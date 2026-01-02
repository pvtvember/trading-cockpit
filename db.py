"""
Database Module for Trading Cockpit
====================================
Add this file to your existing trading-cockpit folder.
Provides PostgreSQL on Railway, JSON locally.
"""

import os
import json
from datetime import datetime

DATABASE_URL = os.getenv('DATABASE_URL', '')
USE_POSTGRES = bool(DATABASE_URL)

# ============== POSTGRES ==============
if USE_POSTGRES:
    try:
        import psycopg2
        from psycopg2.extras import Json
        
        def get_conn():
            return psycopg2.connect(DATABASE_URL)
        
        def init_db():
            """Initialize database tables"""
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        CREATE TABLE IF NOT EXISTS app_data (
                            key TEXT PRIMARY KEY,
                            value JSONB NOT NULL,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                conn.commit()
            print("🐘 PostgreSQL connected - data persists!")
        
        def db_load(key, default=None):
            """Load data from PostgreSQL"""
            try:
                with get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT value FROM app_data WHERE key = %s", (key,))
                        row = cur.fetchone()
                        return row[0] if row else default
            except Exception as e:
                print(f"DB load error ({key}): {e}")
                return default
        
        def db_save(key, value):
            """Save data to PostgreSQL"""
            try:
                with get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute('''
                            INSERT INTO app_data (key, value, updated_at) 
                            VALUES (%s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (key) DO UPDATE SET 
                            value = EXCLUDED.value, 
                            updated_at = CURRENT_TIMESTAMP
                        ''', (key, Json(value)))
                    conn.commit()
            except Exception as e:
                print(f"DB save error ({key}): {e}")
        
        # Initialize on import
        init_db()
        
    except ImportError:
        print("⚠️ psycopg2 not installed, falling back to JSON")
        USE_POSTGRES = False

# ============== JSON FALLBACK ==============
if not USE_POSTGRES:
    DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"📁 Using local JSON storage in {DATA_DIR}")
    
    def db_load(key, default=None):
        """Load data from JSON file"""
        try:
            path = os.path.join(DATA_DIR, f'{key}.json')
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"JSON load error ({key}): {e}")
        return default
    
    def db_save(key, value):
        """Save data to JSON file"""
        try:
            path = os.path.join(DATA_DIR, f'{key}.json')
            with open(path, 'w') as f:
                json.dump(value, f, indent=2, default=str)
        except Exception as e:
            print(f"JSON save error ({key}): {e}")


# ============== HELPER CLASSES ==============

class PersistentDict:
    """
    A dictionary that auto-saves to database.
    Use this to replace your in-memory dictionaries.
    
    Example:
        positions = PersistentDict('positions')
        positions['ABC_123'] = {...}  # Auto-saves
        del positions['ABC_123']       # Auto-saves
    """
    
    def __init__(self, key, default=None):
        self._key = key
        self._data = db_load(key, default or {})
    
    def __getitem__(self, key):
        return self._data[key]
    
    def __setitem__(self, key, value):
        self._data[key] = value
        db_save(self._key, self._data)
    
    def __delitem__(self, key):
        if key in self._data:
            del self._data[key]
            db_save(self._key, self._data)
    
    def __contains__(self, key):
        return key in self._data
    
    def __len__(self):
        return len(self._data)
    
    def __iter__(self):
        return iter(self._data)
    
    def get(self, key, default=None):
        return self._data.get(key, default)
    
    def keys(self):
        return self._data.keys()
    
    def values(self):
        return self._data.values()
    
    def items(self):
        return self._data.items()
    
    def update(self, data):
        self._data.update(data)
        db_save(self._key, self._data)
    
    def pop(self, key, default=None):
        value = self._data.pop(key, default)
        db_save(self._key, self._data)
        return value
    
    def save(self):
        """Force save"""
        db_save(self._key, self._data)
    
    def reload(self):
        """Reload from database"""
        self._data = db_load(self._key, {})


class PersistentList:
    """
    A list that auto-saves to database.
    
    Example:
        journal = PersistentList('journal')
        journal.append({...})  # Auto-saves
    """
    
    def __init__(self, key, default=None):
        self._key = key
        self._data = db_load(key, default or [])
    
    def __getitem__(self, index):
        return self._data[index]
    
    def __setitem__(self, index, value):
        self._data[index] = value
        db_save(self._key, self._data)
    
    def __len__(self):
        return len(self._data)
    
    def __iter__(self):
        return iter(self._data)
    
    def append(self, value):
        self._data.append(value)
        db_save(self._key, self._data)
    
    def insert(self, index, value):
        self._data.insert(index, value)
        db_save(self._key, self._data)
    
    def pop(self, index=-1):
        value = self._data.pop(index)
        db_save(self._key, self._data)
        return value
    
    def save(self):
        db_save(self._key, self._data)
    
    def reload(self):
        self._data = db_load(self._key, [])


# ============== USAGE ==============
"""
To add persistence to your existing code, just change:

BEFORE:
    positions = {}
    watchlist = {}
    journal = []

AFTER:
    from db import PersistentDict, PersistentList
    positions = PersistentDict('positions')
    watchlist = PersistentDict('watchlist') 
    journal = PersistentList('journal')

That's it! Everything else works the same.
"""
