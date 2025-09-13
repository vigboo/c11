import re, os, io
from pathlib import Path

root = Path(__file__).resolve().parents[1]
yaml_path = root / 'users.yml'
index_path = root / 'www' / 'index.html'
contacts_path = root / 'www' / 'contacts.html'

# Read users.yml as UTF-8 (replace errors to survive codepage mismatches while we preserve visible text)
text = yaml_path.read_text(encoding='utf-8', errors='replace')

# Parse a minimal subset of YAML for staff: entries like
# staff:\n  userX:\n    name: ...\n    mail: ...\n    role: ...
staff = []
in_staff = False
cur_indent = None
current = None
for line in text.splitlines():
    if not in_staff:
        if re.match(r'^staff\s*:\s*$', line):
            in_staff = True
        continue
    # stop if next top-level
    if re.match(r'^\S', line):
        break
    # detect user block start
    m_user = re.match(r'^(\s*)([^:#]+):\s*$', line)
    if m_user:
        indent = len(m_user.group(1))
        key = m_user.group(2).strip()
        # only consider keys directly under staff (indent > 0)
        if cur_indent is None:
            cur_indent = indent
        if indent == cur_indent and key:
            if current:
                staff.append(current)
            current = {'_key': key}
        continue
    # inside a user mapping
    m_kv = re.match(r'^(\s+)(name|mail|role)\s*:\s*(.*)\s*$', line)
    if m_kv and current is not None:
        k = m_kv.group(2)
        v = m_kv.group(3)
        # strip surrounding quotes if any
        v = re.sub(r'^[\"\']?(.*?)[\"\']?$', r'\1', v)
        current[k] = v

if current:
    staff.append(current)

if not staff:
    raise SystemExit('No staff entries found in users.yml')

# Extract <style> from index.html to reuse look & feel
style = ''
try:
    idx = index_path.read_text(encoding='utf-8', errors='replace')
    m = re.search(r'<style>([\s\S]*?)</style>', idx, re.IGNORECASE)
    if m:
        style = m.group(1)
except FileNotFoundError:
    pass

# Build HTML
head = ['<!doctype html>',
        '<html lang="ru">',
        '  <head>',
        '    <meta charset="utf-8" />',
        '    <meta name="viewport" content="width=device-width, initial-scale=1" />',
        '    <title>Контакты — DarkStore</title>']
if style:
    head += ['    <style>', style, '    </style>']
head += ['  </head>', '  <body>', '    <div class="container">']

nav = [
  '      <header>',
  '        <div class="brand"><span>DarkStore</span></div>',
  '        <nav>',
  '          <a href="/index.html">Главная</a>',
  '          <a href="/contacts.html" aria-current="page">Контакты</a>',
  '        </nav>',
  '      </header>'
]

body = ['      <section class="section">',
        '        <h1>Контакты</h1>',
        '        <div class="grid" role="list">']
for p in staff:
    name = p.get('name','')
    role = p.get('role','')
    mail = p.get('mail','')
    # ensure domain
    if '@' in mail:
        user, dom = mail.split('@',1)
        mail = f"{user}@darkstore.local"
    else:
        mail = f"{mail}@darkstore.local" if mail else ''
    card = [
        '          <article class="card" role="listitem">',
        '            <div class="body">',
        f'              <h3 class="title">{name}</h3>',
        f'              <p class="desc">{role}</p>',
        f'              <div class="meta"><a class="btn" href="mailto:{mail}">{mail}</a></div>',
        '            </div>',
        '          </article>'
    ]
    body += card
body += ['        </div>', '      </section>']

foot = ['      <footer>',
        '        <a href="/index.html" style="color:#94a3b8;text-decoration:none">← На главную</a>',
        '      </footer>',
        '    </div>',
        '  </body>',
        '</html>']

html = '\n'.join(head + nav + body + foot)
contacts_path.parent.mkdir(parents=True, exist_ok=True)
contacts_path.write_text(html, encoding='utf-8')
print(f'Generated {contacts_path}')
