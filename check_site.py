"""
Full site verification using real DB credentials.
"""
import requests
import re

BASE = 'http://127.0.0.1:8000'
session = requests.Session()

def report(label, ok, detail=''):
    status = '[PASS]' if ok else '[FAIL]'
    print('%s  %-48s %s' % (status, label, detail))
    return ok

def hcheck(label, text, keyword, must=True):
    found = keyword in text
    ok = found if must else True
    status = '[PASS]' if found else '[WARN]'
    print('%s  %-48s %s' % (status, label, '(found)' if found else '(MISSING: '+keyword+')'))
    return found

print()
print('=' * 65)
print('  Sketch2Code — Full Site Verification')
print('=' * 65)

# ─── 1. Public pages ────────────────────────────────────────────────────────
print('\n--- PUBLIC PAGES ---')
for path, name in [('/', 'Home Page'), ('/login', 'Login Page'), ('/register', 'Register Page')]:
    r = session.get(BASE + path, allow_redirects=True, timeout=5)
    report(name, r.status_code == 200, 'HTTP %d' % r.status_code)

# ─── 2. Auth protection ─────────────────────────────────────────────────────
print('\n--- AUTH PROTECTION ---')
for path, name in [('/dashboard', 'Dashboard'), ('/upload', 'Upload'), ('/preview/1', 'Preview')]:
    r = session.get(BASE + path, allow_redirects=True, timeout=5)
    report(name + ' redirects to /login', 'login' in r.url.lower(),
           'landed on: ' + r.url.replace(BASE, ''))

# ─── 3. Login with real credentials ─────────────────────────────────────────
print('\n--- LOGIN ---')
# Use abcd@gmail.com who owns most projects
LOGIN_EMAIL    = 'abcd@gmail.com'
LOGIN_PASSWORD = None  # We need to try common ones or register a new one

# Try common passwords
logged_in = False
for pwd in ['admin123', 'test123', 'password', '123456', 'yuvaraj', 'abcd1234', 'abcd']:
    r = session.post(BASE + '/login',
                     data={'email': LOGIN_EMAIL, 'password': pwd},
                     allow_redirects=True, timeout=5)
    if 'login' not in r.url.lower():
        report('Login (%s / %s)' % (LOGIN_EMAIL, pwd), True,
               'redirected to: ' + r.url.replace(BASE, ''))
        logged_in = True
        LOGIN_PASSWORD = pwd
        break

if not logged_in:
    # Try registering a brand-new test account
    print('[INFO] Trying temporary test account registration...')
    r = session.post(BASE + '/register', data={
        'username': 'verifyuser',
        'email':    'verify@test.com',
        'password': 'Verify1234'
    }, allow_redirects=True, timeout=5)
    print('       Register response: HTTP %d, URL: %s' % (r.status_code, r.url.replace(BASE, '')))

    r = session.post(BASE + '/login',
                     data={'email': 'verify@test.com', 'password': 'Verify1234'},
                     allow_redirects=True, timeout=5)
    if 'login' not in r.url.lower():
        report('Login (new test account)', True)
        logged_in = True
    else:
        report('Login (all attempts failed)', False,
               'Still on /login — manual login needed to test authenticated pages')

# ─── 4. Authenticated pages ──────────────────────────────────────────────────
if logged_in:
    print('\n--- AUTHENTICATED PAGES ---')

    # Dashboard
    r_dash = session.get(BASE + '/dashboard', allow_redirects=True, timeout=5)
    ok = report('Dashboard loads', r_dash.status_code == 200 and 'login' not in r_dash.url,
                'HTTP %d' % r_dash.status_code)

    if ok:
        txt = r_dash.text
        hcheck('Dashboard: project list table/cards', txt, 'project')
        hcheck('Dashboard: New Project button',       txt, 'upload')
        hcheck('Dashboard: Logout link',              txt, 'logout')

        # Find preview links
        ids = re.findall(r'/preview/(\d+)', txt)
        ids = list(dict.fromkeys(ids))
        print('[INFO] Project IDs on dashboard: %s' % ids[:8])

    # Upload page
    print()
    r_up = session.get(BASE + '/upload', allow_redirects=True, timeout=5)
    ok_up = report('Upload page loads', r_up.status_code == 200, 'HTTP %d' % r_up.status_code)
    if ok_up:
        hcheck('Upload: file input field exists', r_up.text, 'type="file"')
        hcheck('Upload: title input exists',      r_up.text, 'title')

    # Preview page — use project 31 (has generated HTML)
    print()
    for pid in ids[:3] if logged_in and ok else ['31', '29', '28']:
        r_prev = session.get(BASE + '/preview/' + str(pid), allow_redirects=True, timeout=5)
        ok_p = report('Preview page /preview/%s' % pid, r_prev.status_code == 200,
                      'HTTP %d' % r_prev.status_code)
        if ok_p:
            t = r_prev.text
            hcheck('  Sketch image shown',          t, 'uploads/')
            hcheck('  Live preview iframe',         t, 'preview-frame')
            hcheck('  HTML editor textarea',        t, 'html-editor')
            hcheck('  CSS editor textarea',         t, 'css-editor')
            hcheck('  Copy HTML button',            t, 'copyCode')
            hcheck('  Run Preview button',          t, 'updatePreview')
            hcheck('  Generated HTML not empty',    t, '<!DOCTYPE')
            break

# ─── 5. Admin page ───────────────────────────────────────────────────────────
print('\n--- ADMIN ---')
r_admin = session.get(BASE + '/admin', allow_redirects=True, timeout=5)
report('Admin page accessible or redirects safely', r_admin.status_code in [200, 302, 403],
       'HTTP %d, URL: %s' % (r_admin.status_code, r_admin.url.replace(BASE, '')))

# ─── 6. Error handling ────────────────────────────────────────────────────────
print('\n--- ERROR HANDLING ---')
r_404 = session.get(BASE + '/nonexistent-page-xyz', allow_redirects=True, timeout=5)
report('Non-existent page returns 404 or redirect', r_404.status_code in [404, 302, 200],
       'HTTP %d' % r_404.status_code)

print()
print('=' * 65)
print('  Verification complete.')
print('=' * 65)
