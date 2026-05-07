import os

files = ['booth.html', 'candidate.html', 'election_date.html', 'news.html', 'results.html', 'help.html']

for f in files:
    path = os.path.join('templates', f)
    with open(path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    if '<main' in content:
        start = content.find('<main')
        end = content.rfind('</main>') + 7
        main_content = content[start:end]
        
        new_content = '{% extends "base.html" %}\n{% block content %}\n' + main_content + '\n{% endblock %}'
        
        with open(path, 'w', encoding='utf-8') as file:
            file.write(new_content)
        print('Updated', f)
    else:
        print('Could not find main in', f)
