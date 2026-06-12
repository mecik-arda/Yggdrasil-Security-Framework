import json

with open(r'C:\Users\ardam\Desktop\linux-command-handbook\data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for category in data:
    print(f"Kategori: {category.get('cat')}")
    cmds = [cmd.get('name') for cmd in category.get('cmds', [])]
    print(f"  Komutlar: {', '.join(cmds)}")
