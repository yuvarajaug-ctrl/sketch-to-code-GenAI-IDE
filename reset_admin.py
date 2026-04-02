import os
from database.db import get_db_connection
from werkzeug.security import generate_password_hash

conn = get_db_connection()
cursor = conn.cursor(dictionary=True)
hashed_pw = generate_password_hash('admin123')
cursor.execute("UPDATE users SET role='admin', password_hash=%s WHERE email='admin@example.com'", (hashed_pw,))
conn.commit()

cursor.execute("SELECT email, role FROM users WHERE email='admin@example.com'")
print(cursor.fetchone())
conn.close()
