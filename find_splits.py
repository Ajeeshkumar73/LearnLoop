import os
import re

def find_split_tags(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Find {% ... %} spanning multiple lines
                splits = re.findall(r'\{%[^%]*\n[^%]*%\}', content)
                for s in splits:
                    print(f"SPLIT TAG in {path}: {repr(s)}")
                
                # Find {{ ... }} spanning multiple lines
                splits = re.findall(r'\{\{[^{}]*\n[^{}]*\}\}', content)
                for s in splits:
                    print(f"SPLIT VARIABLE in {path}: {repr(s)}")

find_split_tags('backend')
