#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open(r'c:\Users\HZ902\OneDrive\Desktop\academy_dashboard\project_backups\backup_2026-02-22_full\templates\analytics.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and remove the old select element lines
new_lines = []
skip_next = 0

for i, line in enumerate(lines):
    if skip_next > 0:
        skip_next -= 1
        continue
    
    # Skip the old select element (lines 86-89 in the current file)
    if 'window.location.href=\'/analytics?year=\'+this.value' in line:
        # Skip this line and the next 3 lines
        skip_next = 3
        continue
    
    # Fix rupee symbol if it's corrupted
    line = line.replace('?{{', '₹{{')
    
    new_lines.append(line)

# Write back
with open(r'c:\Users\HZ902\OneDrive\Desktop\academy_dashboard\project_backups\backup_2026-02-22_full\templates\analytics.html', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Template fixed successfully!")
print(f"Removed {len(lines) - len(new_lines)} lines")
