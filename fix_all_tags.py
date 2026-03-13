import re
import os

def fix_split_tags_in_dir(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Regex to find {% block %} and {{ var }} spanning multiple lines
                # and replace newlines/extra spaces with a single space.
                
                def merge_tag(match):
                    return re.sub(r'\s+', ' ', match.group(0))

                new_content = re.sub(r'\{%.*?%\}', merge_tag, content, flags=re.DOTALL)
                new_content = re.sub(r'\{\{.*?\}\}', merge_tag, new_content, flags=re.DOTALL)

                if new_content != content:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Fixed split tags in {path}")

# Run for the templates directory
fix_split_tags_in_dir(r'd:\LearnLoop2.0 - Copy\backend\main\templates')
