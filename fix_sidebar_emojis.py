#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open(r'c:\Users\HZ902\OneDrive\Desktop\academy_dashboard\project_backups\backup_2026-02-22_full\templates\analytics.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the sidebar section with proper emojis
old_sidebar = '''    <aside class="sidebar">
        <div class="brand">?? Hrishikesh</div>
        <a href="/dashboard" class="nav-link">?? Dashboard</a>
        <a href="/analytics" class="nav-link active">?? Analytics</a>
        <a href="/coaches" class="nav-link">??? Coaches</a>
        <a href="/leaves" class="nav-link">?? Leaves</a>
        <a href="/tasks" class="nav-link">? Tasks</a>
        <a href="/centers" class="nav-link">?? All Centers</a>
        <a href="/backups" class="nav-link">?? Backups</a>
        <a href="/settings" class="nav-link">? Settings</a>
        <a href="/logout" class="nav-link">?? Logout</a>
    </aside>'''

new_sidebar = '''    <aside class="sidebar">
        <div class="brand">🏸 Hrishikesh</div>
        <a href="/dashboard" class="nav-link">📊 Dashboard</a>
        <a href="/analytics" class="nav-link active">📈 Analytics</a>
        <a href="/coaches" class="nav-link">🏋️ Coaches</a>
        <a href="/leaves" class="nav-link">🗓 Leaves</a>
        <a href="/tasks" class="nav-link">✅ Tasks</a>
        <a href="/centers" class="nav-link">🏢 All Centers</a>
        <a href="/backups" class="nav-link">🗄 Backups</a>
        <a href="/settings" class="nav-link">⚙ Settings</a>
        <a href="/logout" class="nav-link">🚪 Logout</a>
    </aside>'''

content = content.replace(old_sidebar, new_sidebar)

with open(r'c:\Users\HZ902\OneDrive\Desktop\academy_dashboard\project_backups\backup_2026-02-22_full\templates\analytics.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Sidebar emojis fixed!")
