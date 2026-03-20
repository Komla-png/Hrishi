#!/usr/bin/env python3

file_path = r'c:\Users\HZ902\OneDrive\Desktop\academy_dashboard\project_backups\backup_2026-02-22_full\templates\analytics.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the duplicate sidebar-header issue
broken = '''        <div class="sidebar-header">
            <div class="sidebar-header">
            <div class="brand">🏸 Hrishikesh</div>
            <button class="sidebar-toggle" id="sidebarToggle" title="Toggle sidebar">☰</button>
        </div>
            <button class="sidebar-toggle" id="sidebarToggle" title="Toggle sidebar">☰</button>
        </div>'''

fixed = '''        <div class="sidebar-header">
            <div class="brand">🏸 Hrishikesh</div>
            <button class="sidebar-toggle" id="sidebarToggle" title="Toggle sidebar">☰</button>
        </div>'''

content = content.replace(broken, fixed)

# Add the JavaScript toggle script before the closing script tag of updateFilters
old_script_end = '''        function updateFilters() {
            const year = document.getElementById('yearSelect').value;
            const fromMonth = document.getElementById('fromMonth').value;
            const toMonth = document.getElementById('toMonth').value;
            window.location.href = `/analytics?year=${year}&from_month=${fromMonth}&to_month=${toMonth}`;
        }
        </script>'''

new_script = '''        function updateFilters() {
            const year = document.getElementById('yearSelect').value;
            const fromMonth = document.getElementById('fromMonth').value;
            const toMonth = document.getElementById('toMonth').value;
            window.location.href = `/analytics?year=${year}&from_month=${fromMonth}&to_month=${toMonth}`;
        }
        </script>

        <script>
        // Sidebar toggle functionality
        document.addEventListener('DOMContentLoaded', function() {
            const layout = document.getElementById('analyticsLayout');
            const sidebar = document.getElementById('analyticsSidebar');
            const toggleBtn = document.getElementById('sidebarToggle');
            
            // Load preference from localStorage
            const isCollapsed = localStorage.getItem('analyticsSidebarCollapsed') === 'true';
            if (isCollapsed) {
                layout.classList.add('sidebar-collapsed');
            }
            
            // Toggle on button click
            toggleBtn.addEventListener('click', function() {
                layout.classList.toggle('sidebar-collapsed');
                const collapsed = layout.classList.contains('sidebar-collapsed');
                localStorage.setItem('analyticsSidebarCollapsed', collapsed);
            });
        });
        </script>'''

content = content.replace(old_script_end, new_script)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed analytics.html sidebar and added toggle JavaScript')
