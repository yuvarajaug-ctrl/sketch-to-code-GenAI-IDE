import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('site.db')
cursor = conn.cursor()
cursor.execute("UPDATE users SET password_hash = ? WHERE email = 'abcd@gmail.com'", (generate_password_hash('password123'),))
conn.commit()
conn.close()
print('Password updated for abcd@gmail.com')
