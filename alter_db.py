import sqlite3
import os

db_path = os.path.join(os.getcwd(), 'site.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()

try:
    cur.execute("ALTER TABLE projects ADD COLUMN detected_elements TEXT")
    print("Added detected_elements column to projects table")
except sqlite3.OperationalError as e:
    print("Column might already exist:", e)

conn.commit()
conn.close()
