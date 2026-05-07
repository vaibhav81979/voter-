import os

files = [
    'templates/admin/dashboard.html',
    'templates/admin/voters.html',
    'templates/admin/fraud_alerts.html',
    'templates/admin/login.html',
    'templates/epic_recovery.html'
]

replacements = {
    '"../welcome.html"': '"{{ url_for(\'voter.welcome\') }}"',
    '"../index.html"': '"{{ url_for(\'voter.home\') }}"',
    '"../login.html"': '"{{ url_for(\'voter.login\') }}"',
    '"../register.html"': '"{{ url_for(\'voter.register\') }}"',
    '"../booth.html"': '"{{ url_for(\'voter.booth\') }}"',
    '"../candidate.html"': '"{{ url_for(\'voter.candidate\') }}"',
    '"../results.html"': '"{{ url_for(\'voter.results\') }}"',
    '"../help.html"': '"{{ url_for(\'voter.help_page\') }}"',
    '"dashboard.html"': '"{{ url_for(\'admin.dashboard\') }}"',
    '"voters.html"': '"{{ url_for(\'admin.voters\') }}"',
    '"fraud_alerts.html"': '"{{ url_for(\'admin.fraud_alerts\') }}"',
    '"login.html"': '"{{ url_for(\'admin.admin_login\') }}"',
    '"index.html"': '"{{ url_for(\'voter.home\') }}"',
    '"election_date.html"': '"{{ url_for(\'voter.election_date\') }}"',
    '"news.html"': '"{{ url_for(\'voter.news\') }}"',
    '"epic_recovery.html"': '"{{ url_for(\'voter.epic_recovery\') }}"'
}

for f in files:
    if not os.path.exists(f): continue
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
        
    for old, new in replacements.items():
        content = content.replace(old, new)
        
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
    print(f'Fixed links in {f}')
