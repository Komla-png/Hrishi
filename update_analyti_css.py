#!/usr/bin/env python3

file_path = r'c:\Users\HZ902\OneDrive\Desktop\academy_dashboard\project_backups\backup_2026-02-22_full\templates\analytics.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Update CSS for sidebar collapse functionality
old_css = '''        .layout { display:grid; grid-template-columns:220px 1fr; min-height:100vh; }
        .sidebar { position:sticky; top:0; height:100vh; background:#0b1222; border-right:1px solid #1f2a44; padding:18px 12px; }
        .brand { font-size:18px; font-weight:800; margin:8px 8px 16px; color:#dbeafe; }
        .nav-link { display:flex; gap:10px; align-items:center; color:#d1d5db; text-decoration:none; border-radius:10px; padding:10px 12px; margin:4px 0; }
        .nav-link:hover, .nav-link.active { background:#1d4ed8; color:#fff; }'''

new_css = '''        .layout { display:grid; grid-template-columns:220px 1fr; min-height:100vh; transition:grid-template-columns 0.2s; }
        .layout.sidebar-collapsed { grid-template-columns:60px 1fr; }
        .sidebar { position:sticky; top:0; height:100vh; background:#0b1222; border-right:1px solid #1f2a44; padding:18px 12px; display:flex; flex-direction:column; transition:width 0.2s; }
        .sidebar-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; }
        .sidebar-toggle { background:0; border:0; color:#dbeafe; cursor:pointer; font-size:20px; padding:8px; }
        .brand { font-size:18px; font-weight:800; margin:0; color:#dbeafe; }
        .layout.sidebar-collapsed .brand { display:none; }
        .layout.sidebar-collapsed .sidebar-text { display:none; }
        .nav-link { display:flex; gap:10px; align-items:center; color:#d1d5db; text-decoration:none; border-radius:10px; padding:10px 12px; margin:4px 0; white-space:nowrap; }
        .nav-link:hover, .nav-link.active { background:#1d4ed8; color:#fff; }
        .layout.sidebar-collapsed .nav-link { justify-content:center; padding:10px 0; }
        .layout.sidebar-collapsed .nav-link span { display:none; }'''

content = content.replace(old_css, new_css)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated CSS for sidebar collapse')
