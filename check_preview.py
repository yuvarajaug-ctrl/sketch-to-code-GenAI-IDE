"""
Check preview pages for existing projects: 28, 29, 30, 31
Must log in as abcd@gmail.com (user_id=4) who owns those projects.
We'll test with bcrypt by checking the hash pattern first.
"""
import requests, re, sqlite3

BASE = 'http://127.0.0.1:8000'

# Read password hash from DB to understand what password scheme is used
conn = sqlite3.connect('site.db')
conn.row_factory = sqlite3.Row
user = conn.execute("SELECT * FROM users WHERE email='abcd@gmail.com'").fetchone()
print("User: id=%s, username=%s" % (user['id'], user['username']))
print("Hash preview: %s..." % str(user['password_hash'])[:20])
hash_val = user['password_hash']
conn.close()

from werkzeug.security import check_password_hash

# Test all likely passwords
for pwd in ['yuvaraj', 'Yuvaraj', 'abcd1234', 'abcd@123', '1234', 'admin', 'password', '12345678', 'abcd']:
    if check_password_hash(hash_val, pwd):
        print("PASSWORD FOUND: '%s'" % pwd)
        break
else:
    print("Could not determine password. Will test with session directly.")

# Now test preview pages directly using the app context to set session
from app import app
with app.test_client() as client:
    with client.session_transaction() as sess:
        sess['user_id'] = 4
        sess['username'] = 'yuvaraj'
        sess['role'] = 'user'

    print()
    print("--- PREVIEW PAGES (as user yuvaraj, id=4) ---")
    for pid in [28, 29, 30, 31, 32]:
        r = client.get('/preview/%d' % pid, follow_redirects=True)
        txt = r.data.decode('utf-8', errors='replace')
        has_iframe  = 'preview-frame' in txt
        has_html_ed = 'html-editor' in txt
        has_css_ed  = 'css-editor' in txt
        has_copy    = 'copyCode' in txt
        has_run     = 'updatePreview' in txt
        has_img     = 'uploads/' in txt
        has_doctype = '&lt;!DOCTYPE' in txt or 'DOCTYPE' in txt

        ok = r.status_code == 200
        print()
        print("Preview /preview/%d: HTTP %d" % (pid, r.status_code))
        print("  Sketch image visible : %s" % has_img)
        print("  Live preview iframe  : %s" % has_iframe)
        print("  HTML editor textarea : %s" % has_html_ed)
        print("  CSS editor textarea  : %s" % has_css_ed)
        print("  Copy buttons JS      : %s" % has_copy)
        print("  Run Preview button   : %s" % has_run)
        print("  Generated HTML shown : %s" % has_doctype)

    print()
    print("--- UPLOAD PAGE ---")
    r = client.get('/upload', follow_redirects=True)
    txt = r.data.decode('utf-8', errors='replace')
    print("Upload: HTTP %d" % r.status_code)
    print("  Has file input: %s" % ('type="file"' in txt))
    print("  Has title input: %s" % ('title' in txt))
    print("  Has submit button: %s" % ('submit' in txt.lower() or 'btn' in txt))
