import subprocess
import sys
import re

html_path = r'..\bleeding_edge.html'
with open(html_path, encoding='utf-8') as f:
    content = f.read()

matches = list(re.finditer(r'<script\b([^>]*)>(.*?)</script>', content, re.DOTALL))
print(f'Found {len(matches)} script tag(s).')

for i, m in enumerate(matches):
    attrs = m.group(1)
    body = m.group(2)
    if 'text/plain' in attrs:
        print(f'Script {i} is text/plain, skipping.')
        continue
    p = subprocess.run(['node', '--check', '-'], input=body, text=True, capture_output=True)
    if p.returncode != 0:
        print(f'Script {i} failed syntax check:')
        print(p.stderr)
        sys.exit(1)
    else:
        label = attrs.strip() or 'inline JS'
        print(f'Script {i} ({label}): node --check PASSED.')

print('ALL JAVASCRIPT SYNTAX CHECKS PASSED!')
