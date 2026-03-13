import re
import os

def fix_split_tags(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # This regex looks for split template tags.
    # We want to catch instances where a tag starts with {% or {{ on one line and ends with %} or }} on the next line(s).
    # However, for template logic, it's safer to just look for specific common patterns that are split.
    
    # Pattern 1: {% else %}...{% endif %}
    content = re.sub(r'\{% else\s*%\}\s*([^%]*?)\s*\{%\s*endif\s*%\}', r'{% else %}\1{% endif %}', content, flags=re.DOTALL)
    
    # Pattern 2: Specific common splits in this project
    replacements = [
        (r'\{% if profile\.full_name %\}\{\{ profile\.full_name \}\}\s*\{% else\s*%\}\s*Missing\s*\{%\s*endif\s*%\}', 
         r'{% if profile.full_name %}{{ profile.full_name }}{% else %}Missing{% endif %}'),
        
        (r'\{\{ user_email\s*\}\}', r'{{ user_email }}'),
        
        (r'\{% if profile\.phone %\}\{\{ profile\.phone \}\}\s*\{% else\s*%\}\s*Missing\s*\{%\s*endif\s*%\}', 
         r'{% if profile.phone %}{{ profile.phone }}{% else %}Missing{% endif %}'),
        
        (r'\{% if profile\.education %\}\{\{ profile\.education \}\}\s*\{% else\s*%\}\s*Missing\s*\{%\s*endif\s*%\}', 
         r'{% if profile.education %}{{ profile.education }}{% else %}Missing{% endif %}'),
        
        (r'\{% if profile\.current_skills %\}Added\s*\{% else\s*%\}\s*Add skills for\s*better resume\s*\{%\s*endif\s*%\}', 
         r'{% if profile.current_skills %}Added{% else %}Add skills for better resume{% endif %}')
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    # General fix for split {{ ... }} and {% ... %} that are purely whitespace/newline split
    content = re.sub(r'\{\{\s*([^{}\n]*?)\n\s*\}\}', r'{{ \1 }}', content)
    content = re.sub(r'\{%\s*([^%{}\n]*?)\n\s*%\}', r'{% \1 %}', content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Processed {file_path}")

fix_split_tags(r'd:\LearnLoop2.0 - Copy\backend\main\templates\profile_page.html')
