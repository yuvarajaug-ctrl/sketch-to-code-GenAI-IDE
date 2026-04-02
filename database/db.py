import sqlite3
import os
import re
from config import Config

DB_PATH = os.path.join(os.getcwd(), 'site.db')

class SQLiteConnection:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
    def cursor(self, dictionary=False):
        return SQLiteCursor(self.conn.cursor(), dictionary)
        
    def commit(self):
        self.conn.commit()
        
    def close(self):
        self.conn.close()
        
    @property
    def lastrowid(self):
        # This is a bit tricky, but in the routes they usually use cursor.lastrowid
        return None

class SQLiteCursor:
    def __init__(self, cursor, dictionary=False):
        self.cursor = cursor
        self.dictionary = dictionary
        
    def execute(self, sql, params=None):
        # Replace MySQL %s with SQLite ?
        sql = sql.replace('%s', '?')
        
        # Handle some MySQL specific keywords if necessary
        # (e.g., AUTO_INCREMENT is already handled in schema init)
        
        if params is None:
            return self.cursor.execute(sql)
        
        # Ensure params is a tuple if only one arg is passed as %s
        if not isinstance(params, (list, tuple)):
            params = (params,)
            
        return self.cursor.execute(sql, params)
        
    def fetchone(self):
        row = self.cursor.fetchone()
        if row and self.dictionary:
            return dict(row)
        return row
        
    def fetchall(self):
        rows = self.cursor.fetchall()
        if self.dictionary:
            return [dict(r) for r in rows]
        return rows

    @property
    def lastrowid(self):
        return self.cursor.lastrowid

def get_db_connection():
    # If site.db doesn't exist, create it with schema
    if not os.path.exists(DB_PATH):
        init_db()
    
    return SQLiteConnection(DB_PATH)

def init_db():
    schema_path = os.path.join(os.getcwd(), 'database', 'schema.sql')
    if not os.path.exists(schema_path):
        # Try finding it in the project root if not in database/
        schema_path = os.path.join(os.getcwd(), 'schema.sql')
        
    if not os.path.exists(schema_path):
        print(f"SCHEMA NOT FOUND: {schema_path}")
        return

    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    # SQLite compatibility transformations
    schema_sql = schema_sql.replace('AUTO_INCREMENT PRIMARY KEY', 'PRIMARY KEY AUTOINCREMENT')
    schema_sql = schema_sql.replace('INT ', 'INTEGER ')
    schema_sql = schema_sql.replace('TIMESTAMP DEFAULT CURRENT_TIMESTAMP', 'DATETIME DEFAULT CURRENT_TIMESTAMP')
    schema_sql = re.sub(r"ENUM\([^)]+\)", "TEXT", schema_sql)
    schema_sql = schema_sql.replace('CREATE DATABASE IF NOT EXISTS sketch2code_db;', '')
    schema_sql = schema_sql.replace('USE sketch2code_db;', '')
    
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(schema_sql)
        conn.commit()
        print("SQLite Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing SQLite DB: {e}")
    finally:
        conn.close()
