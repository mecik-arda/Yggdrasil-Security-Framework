import re
f = open('templates/index.html', 'r', encoding='utf-8')
c = f.read()
f.close()
m = re.search(r'<script>(.*?loadTools.*?)</script>', c, re.DOTALL)
if m:
    s = m.group(1)
    s = re.sub(r'\{\{.*?\}\}', '""', s)
    open('temp2.js', 'w', encoding='utf-8').write(s)
    import subprocess
    result = subprocess.run(['node', '-c', 'temp2.js'], capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
else:
    print("not found")
