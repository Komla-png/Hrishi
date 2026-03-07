#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open(r'c:\Users\HZ902\OneDrive\Desktop\academy_dashboard\project_backups\backup_2026-02-22_full\templates\analytics.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the stray </div> after </script>
content = content.replace('        </script>\n        </div>\n\n        <section class="cards">',
                          '        </script>\n\n        <section class="cards">')

with open(r'c:\Users\HZ902\OneDrive\Desktop\academy_dashboard\project_backups\backup_2026-02-22_full\templates\analytics.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Stray div removed!")
