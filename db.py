"""
Database Module - PostgreSQL on Railway, JSON locally
"""
import os
import json

DATABASE_URL = os.getenv('DATABASE_URL', '')
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    try:
        import psycopg2
        from psycopg2.extras import Json
        
        def get_conn():
            return psycopg2.connect(DATABASE_URL)
        
        def init_db():
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute('''CREATE TABLE IF NOT EXISTS app_data (
                        key TEXT PRIMARY KEY,
                        value JSONB NOT NULL
                    )''')
                conn.commit()
            print("🐘 PostgreSQL connected")
        
        def db_load(key, default=None):
            try:
                with get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT value FROM app_data WHERE key = %s", (key,))
                        row = cur.fetchone()
                        return row[0] if row else default
            except:
                return default
        
        def db_save(key, value):
            try:
                with get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute('''INSERT INTO app_data (key, value) VALUES (%s, %s)
                            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value''',
                            (key, Json(value)))
                    conn.commit()
            except Exception as e:
                print(f"DB save error: {e}")
        
        init_db()
    except ImportError:
        USE_POSTGRES = False

if not USE_POSTGRES:
    DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"📁 Using local JSON storage")
    
    def db_load(key, default=None):
        try:
            path = os.path.join(DATA_DIR, f'{key}.json')
            if os.path.exists(path):
                with open(path) as f:
                    return json.load(f)
        except:
            pass
        return default
    
    def db_save(key, value):
        try:
            with open(os.path.join(DATA_DIR, f'{key}.json'), 'w') as f:
                json.dump(value, f, indent=2, default=str)
        except Exception as e:
            print(f"Save error: {e}")


class PersistentDict:
    """Dict that auto-saves to database"""
    def __init__(self, key, default=None):
        self._key = key
        self._data = db_load(key, default or {})
    
    def __getitem__(self, key): return self._data[key]
    def __setitem__(self, key, value):
        self._data[key] = value
        db_save(self._key, self._data)
    def __delitem__(self, key):
        if key in self._data:
            del self._data[key]
            db_save(self._key, self._data)
    def __contains__(self, key): return key in self._data
    def __len__(self): return len(self._data)
    def __iter__(self): return iter(self._data)
    def get(self, key, default=None): return self._data.get(key, default)
    def keys(self): return self._data.keys()
    def values(self): return self._data.values()
    def items(self): return self._data.items()
    def pop(self, key, default=None):
        v = self._data.pop(key, default)
        db_save(self._key, self._data)
        return v


class PersistentList:
    """List that auto-saves to database"""
    def __init__(self, key, default=None):
        self._key = key
        self._data = db_load(key, default or [])
    
    def __getitem__(self, i): return self._data[i]
    def __len__(self): return len(self._data)
    def __iter__(self): return iter(self._data)
    def append(self, v):
        self._data.append(v)
        db_save(self._key, self._data)
    def insert(self, i, v):
        self._data.insert(i, v)
        db_save(self._key, self._data)
