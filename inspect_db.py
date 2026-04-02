import sqlite3
conn = sqlite3.connect('site.db')
conn.row_factory = sqlite3.Row

tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables:", [t['name'] for t in tables])

try:
    users = conn.execute("SELECT id, email, username FROM users").fetchall()
    print("Users (%d):" % len(users))
    for u in users[:5]:
        print("  id=%s  email=%s  username=%s" % (u['id'], u['email'], u['username']))
    if not users:
        print("  (no users found)")
except Exception as e:
    print("Users error:", e)

try:
    projects = conn.execute("SELECT id, title, user_id, generated_html IS NOT NULL as has_html FROM projects ORDER BY id DESC").fetchall()
    print("Projects (%d):" % len(projects))
    for p in projects[:5]:
        print("  id=%s  title=%s  user_id=%s  has_html=%s" % (p['id'], p['title'], p['user_id'], bool(p['has_html'])))
    if not projects:
        print("  (no projects found)")
except Exception as e:
    print("Projects error:", e)

conn.close()
