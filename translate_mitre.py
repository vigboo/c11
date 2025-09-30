import csv
from deep_translator import GoogleTranslator

input_path = "mitre_technics.csv"
translator = GoogleTranslator(source='auto', target='ru')
cache = {}

def translate(text):
    if text is None:
        return ''
    if not text.strip():
        return text
    key = text.strip()
    if key in cache:
        return cache[key]
    try:
        translated = translator.translate(key)
    except Exception:
        translated = text
    cache[key] = translated
    # preserve leading/trailing whitespace
    prefix_len = len(text) - len(text.lstrip())
    suffix_len = len(text) - len(text.rstrip())
    prefix = text[:prefix_len]
    suffix = text[len(text) - suffix_len:]
    return f"{prefix}{translated}{suffix}"

rows = []
with open(input_path, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f, delimiter=';')
    for row in reader:
        name_val = row.get('название') or row.get('name') or ''
        desc_val = row.get('описание') or row.get('description') or ''
        tactics_val = row.get('тактики') or row.get('tactics') or ''
        row['название'] = translate(name_val)
        row['описание'] = translate(desc_val)
        row['тактики'] = translate(tactics_val)
        rows.append(row)

fieldnames = ['ID', 'название', 'описание', 'тактики', 'platforms']
with open(input_path, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, delimiter=';', fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, '') for field in fieldnames})
