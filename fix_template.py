path = r'd:\LearnLoop2.0 - Copy\backend\main\templates\roadmap_page.html'

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f'Total lines: {len(lines)}')
print()

# Check for any template tags that are split across lines
# A split tag would be a line with {% but no matching %}
import re

for i, line in enumerate(lines):
    stripped = line.rstrip()
    # Count {% and %} occurrences
    opens = len(re.findall(r'\{%', stripped))
    closes = len(re.findall(r'%\}', stripped))
    if opens != closes:
        print(f'POTENTIAL SPLIT TAG at line {i+1}: {repr(stripped)}')
        if i + 1 < len(lines):
            print(f'  Next line {i+2}: {repr(lines[i+1].rstrip())}')
        print()
