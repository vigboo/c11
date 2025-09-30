import csv, requests, urllib.parse, time

input_path = "mitre_technics.csv"
cache = {}

def translate(text):
    if text is None:
        return ''
    original = text
    stripped = text.strip()
    if not stripped:
        return text
    if stripped in cache:
        return cache[stripped]
    params = {
        'client': 'gtx',
        'sl': 'en',
        'tl': 'ru',
        'dt': 't',
        'q': stripped
    }
    url = "https://translate.googleapis.com/translate_a/single"
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        translated = ''.join(chunk[0] for chunk in data[0])
    except Exception as e:
        translated = stripped
    cache[stripped] = translated
    prefix = original[:len(original) - len(original.lstrip())]
    suffix = original[len(original.rstrip()):]
    return f"{prefix}{translated}{suffix}"

with open(input_path, 'r', encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f, delimiter=';'))

for row in rows:
    row['название'] = translate(row.get('название', row.get('name', '')))
    row['описание'] = translate(row.get('описание', row.get('description', '')))
    row['тактики'] = translate(row.get('тактики', row.get('tactics', '')))
    time.sleep(0.1)

fieldnames = ['ID', 'название', 'описание', 'тактики', 'platforms']
with open(input_path, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, delimiter=';', fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
