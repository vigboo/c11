from pathlib import Path
p = Path('www/index.html')
s = p.read_text(encoding='utf-8', errors='replace')
new = s.replace('href="#contacts"', 'href="/contacts.html"')
if new != s:
    p.write_text(new, encoding='utf-8')
    print('updated')
else:
    print('nochange')
