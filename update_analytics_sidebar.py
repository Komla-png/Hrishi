#!/usr/bin/env python3
import re

file_path = r'c:\Users\HZ902\OneDrive\Desktop\academy_dashboard\project_backups\backup_2026-02-22_full\templates\analytics.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the brand section with a header that includes toggle button
old_brand = '        <div class="brand">🏸 Hrishikesh</div>'
new_header = '''        <div class="sidebar-header">
            <div class="brand">🏸 Hrishikesh</div>
            <button class="sidebar-toggle" id="sidebarToggle" title="Toggle sidebar">☰</button>
        </div>'''

content = content.replace(old_brand, new_header)

# Replace nav-links with span-wrapped text
nav_updates = {
    '<a href="/dashboard" class="nav-link">📊 Dashboard</a>': '<a href="/dashboard" class="nav-link">📊 <span class="sidebar-text">Dashboard</span></a>',
    '<a href="/analytics" class="nav-link active">📈 Analytics</a>': '<a href="/analytics" class="nav-link active">📈 <span class="sidebar-text">Analytics</span></a>',
    '<a href="/coaches" class="nav-link">🏋️ Coaches</a>': '<a href="/coaches" class="nav-link">🏋️ <span class="sidebar-text">Coaches</span></a>',
    '<a href="/leaves" class="nav-link">🗓 Leaves</a>': '<a href="/leaves" class="nav-link">🗓 <span class="sidebar-text">Leaves</span></a>',
    '<a href="/tasks" class="nav-link">✅ Tasks</a>': '<a href="/tasks" class="nav-link">✅ <span class="sidebar-text">Tasks</span></a>',
    '<a href="/centers" class="nav-link">🏢 All Centers</a>': '<a href="/centers" class="nav-link">🏢 <span class="sidebar-text">All Centers</span></a>',
    '<a href="/backups" class="nav-link">🗄 Backups</a>': '<a href="/backups" class="nav-link">🗄 <span class="sidebar-text">Backups</span></a>',
    '<a href="/settings" class="nav-link">⚙ Settings</a>': '<a href="/settings" class="nav-link">⚙ <span class="sidebar-text">Settings</span></a>',
    '<a href="/logout" class="nav-link">🚪 Logout</a>': '<a href="/logout" class="nav-link">🚪 <span class="sidebar-text">Logout</span></a>',
}

for old, new in nav_updates.items():
    content = content.replace(old, new)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Successfully updated analytics.html sidebar')
