"""
apply_sidebar_migration.py
Applies the global sidebar migration to all Flask templates.
Creates a _sidebar.html partial and updates every page template.
"""
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(BASE, 'templates')

SIDEBAR_CSS_LINK = '    <link rel="stylesheet" href="/static/sidebar.css">'
SIDEBAR_INCLUDE  = '{% include \'_sidebar.html\' %}'
SB_OPEN          = '<div class="sb-content">'
SB_CLOSE         = '</div><!-- /.sb-content -->'
SIDEBAR_JS_TAG   = '<script src="/static/sidebar.js"></script>'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()

def write(path, content):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print(f'  ✓ written: {os.path.basename(path)}')


def inject_css_link(html):
    """Add sidebar.css link just before </head> (only once)."""
    if '/static/sidebar.css' in html:
        return html
    return html.replace('</head>', SIDEBAR_CSS_LINK + '\n</head>', 1)


def inject_sidebar_include_after_body(html):
    """Replace <body> with <body>\n{% include '_sidebar.html' %} once."""
    if '_sidebar.html' in html:
        return html
    return html.replace('<body>', '<body>\n' + SIDEBAR_INCLUDE, 1)


def wrap_content(html, content_start_marker, insert_before_body_close=True):
    """
    Insert <div class="sb-content"> immediately before content_start_marker,
    and </div><!-- /.sb-content --> + sidebar.js just before </body>.
    """
    if 'sb-content' in html:
        return html
    # Insert opening wrapper
    html = html.replace(content_start_marker,
                        SB_OPEN + '\n' + content_start_marker, 1)
    if insert_before_body_close:
        html = html.replace('</body>',
                            SB_CLOSE + '\n' + SIDEBAR_JS_TAG + '\n</body>', 1)
    return html


def remove_old_sidebar_block(html, start_marker, end_marker):
    """Remove everything from start_marker up to and including end_marker."""
    start = html.find(start_marker)
    end   = html.find(end_marker, start)
    if start == -1 or end == -1:
        return html
    end += len(end_marker)
    # also eat a trailing newline
    if end < len(html) and html[end] == '\n':
        end += 1
    return html[:start] + html[end:]


# ---------------------------------------------------------------------------
# Per-template migration functions
# ---------------------------------------------------------------------------

def migrate_dashboard(html):
    """dashboard.html — has full sidebar HTML + <style> + <script> blocks."""

    # 1. Add sidebar.css link
    html = inject_css_link(html)

    # 2. Replace body + old sidebar block (everything from
    #    '<body>' through the closing sidebar toggle '</script>')
    old_body_start = '<body>\n<div id="sidebar" class="sidebar">'
    sidebar_js_end = 'localStorage.setItem(\'dashboardSidebarCollapsed\', collapsed);\n};\n</script>'

    start = html.find(old_body_start)
    end   = html.find(sidebar_js_end)
    if start != -1 and end != -1:
        end += len(sidebar_js_end)
        # eat trailing newlines/blank lines
        while end < len(html) and html[end] in ('\n', '\r'):
            end += 1
        html = html[:start] + '<body>\n' + SIDEBAR_INCLUDE + '\n' + html[end:]

    # 3. Wrap container in sb-content
    html = wrap_content(html, '<div class="container">')

    return html


def migrate_tasks(html):
    """tasks.html — same sidebar pattern as dashboard."""

    html = inject_css_link(html)

    old_body_start = '<div id="sidebar" class="sidebar">'
    sidebar_js_end = 'localStorage.setItem(\'dashboardSidebarCollapsed\', collapsed);\n};\n</script>'

    start = html.find(old_body_start)
    end   = html.find(sidebar_js_end)
    if start != -1 and end != -1:
        end += len(sidebar_js_end)
        while end < len(html) and html[end] in ('\n', '\r'):
            end += 1
        html = html[:start] + SIDEBAR_INCLUDE + '\n' + html[end:]

    # Wrap container in sb-content
    html = wrap_content(html, '<div class="container">')

    return html


def migrate_grid_layout(html, sidebar_id, layout_id, main_class='main'):
    """
    For analytics_ai.html and summer_camp_incentives.html.
    These use grid layout: <div class="layout"><aside class="sidebar">...</aside><main class="main">
    Strategy:
      1. Add sidebar.css link
      2. Insert global sidebar include right before <div class="layout">
      3. Remove the <apart class="sidebar">…</aside> block
      4. Remove the sidebar-toggle JS inside <main>
      5. Replace <div class="layout"…> with just the layout div but with display:block override,
         or just remove it entirely and use sb-content on the main
      6. Add sb-content class to <main>
    """
    html = inject_css_link(html)

    # Remove old aside sidebar block
    aside_start = f'<aside class="sidebar" id="{sidebar_id}">'
    aside_end   = '</aside>'
    start = html.find(aside_start)
    end   = html.find(aside_end, start) if start != -1 else -1
    if start != -1 and end != -1:
        end += len(aside_end)
        while end < len(html) and html[end] in ('\n', '\r', ' '):
            if html[end] in ('\n', '\r'):
                end += 1
                break
            end += 1
        html = html[:start] + html[end:]

    # Remove the entire .layout wrapper div opening tag (and closing div at the end)
    layout_open_re = re.compile(
        r'<div class="layout(?:[^"]*)"[^>]*id="' + re.escape(layout_id) + r'"[^>]*>')
    html = layout_open_re.sub('', html, count=1)

    # Remove the closing </div> that matched the layout wrapper.
    # It's the </div> right before </body>
    html = html.replace('\n</div>\n\n<script', '\n\n<script', 1)

    # Insert sidebar include right after <body>
    html = inject_sidebar_include_after_body(html)

    # Add sb-content class to <main class="main">
    if 'sb-content' not in html:
        html = html.replace(f'<main class="{main_class}">', 
                            f'<main class="{main_class} sb-content">', 1)

    # Remove old sidebar-toggle JS (the DOMContentLoaded block that references 'analyticsSidebar' or 'pageLayout')
    # Pattern: entire <script>document.addEventListener block with 'analyticsSidebarCollapsed' or variant
    for key in ('analyticsSidebarCollapsed', 'summerCampSidebarCollapsed'):
        script_start = f"localStorage.getItem('{key}')"
        idx = html.find(script_start)
        if idx != -1:
            # find the <script> before it
            script_open = html.rfind('<script>', 0, idx)
            script_close = html.find('</script>', idx)
            if script_open != -1 and script_close != -1:
                script_close += len('</script>')
                while script_close < len(html) and html[script_close] in ('\n', '\r'):
                    script_close += 1
                html = html[:script_open] + html[script_close:]

    # Add sidebar.js before </body>
    if SIDEBAR_JS_TAG not in html:
        html = html.replace('</body>', SIDEBAR_JS_TAG + '\n</body>', 1)

    return html


def migrate_summer_camp(html):
    """summer_camp_incentives.html."""
    html = inject_css_link(html)

    # Remove old aside sidebar block
    aside_start = '<aside class="sidebar" id="pageSidebar">'
    aside_end   = '</aside>'
    start = html.find(aside_start)
    end   = html.find(aside_end, start) if start != -1 else -1
    if start != -1 and end != -1:
        end += len(aside_end)
        while end < len(html) and html[end] in ('\n', '\r'):
            end += 1
        html = html[:start] + html[end:]

    # Remove the opening layout div tag
    html = re.sub(r'<div class="layout"[^>]*id="pageLayout"[^>]*>\s*', '', html, count=1)

    # Remove the closing </div> before </main>\n</div>\n\n<script
    # The layout closing div is right before </body>; let's find and remove it.
    # It appears as </main>\n</div>\n\n (last div before body end)
    html = html.replace('    </main>\n</div>\n\n<script', '    </main>\n<script', 1)

    # Insert sidebar include after <body>
    html = inject_sidebar_include_after_body(html)

    # Add sb-content to <main class="main">
    if 'sb-content' not in html:
        html = html.replace('<main class="main">', '<main class="main sb-content">', 1)

    # Remove old sidebar toggle JS
    key = "summerCampSidebarCollapsed"
    script_start = f"localStorage.getItem('{key}')"
    idx = html.find(script_start)
    if idx != -1:
        script_open = html.rfind('<script>', 0, idx)
        script_close = html.find('</script>', idx)
        if script_open != -1 and script_close != -1:
            script_close += len('</script>')
            while script_close < len(html) and html[script_close] in ('\n', '\r'):
                script_close += 1
            html = html[:script_open] + html[script_close:]

    # Remove sidebar CSS from <head> — the big .layout, .sidebar block in summer_camp
    # These are the layout-specific CSS rules that conflict
    html = re.sub(
        r'\.layout \{[^}]*\}.*?\.layout\.sidebar-collapsed \{[^}]*\}',
        '/* sidebar handled by global sidebar.css */',
        html, flags=re.DOTALL, count=1
    )

    if SIDEBAR_JS_TAG not in html:
        html = html.replace('</body>', SIDEBAR_JS_TAG + '\n</body>', 1)

    return html


def migrate_centers_list(html):
    """centers_list.html — simple fixed sidebar, different styling."""

    html = inject_css_link(html)

    # Remove old sidebar HTML block (from <div class="sidebar"> to </div> before container)
    start_marker = '    <div class="sidebar">'
    # End marker is the </div> that closes the sidebar div
    start = html.find(start_marker)
    if start != -1:
        # find closing </div> for the sidebar
        depth = 0
        i = start
        while i < len(html):
            if html[i:i+4] == '<div':
                depth += 1
                i += 4
            elif html[i:i+6] == '</div>':
                depth -= 1
                if depth == 0:
                    end = i + 6
                    # eat trailing whitespace/newline
                    while end < len(html) and html[end] in (' ', '\t'):
                        end += 1
                    if end < len(html) and html[end] == '\n':
                        end += 1
                    html = html[:start] + html[end:]
                    break
                i += 6
            else:
                i += 1

    # Remove old sidebar CSS block (the inline style block in <head>)
    # These have .sidebar, .sidebar-header, .sidebar-title, etc.
    html = re.sub(
        r'\.sidebar \{\s*position: fixed;.*?\.container \{\s*margin-left: 230px;[^}]*\}',
        '/* sidebar styles handled by global sidebar.css */',
        html, flags=re.DOTALL, count=1
    )

    # Also remove old theme toggle script right after the sidebar
    html = re.sub(
        r'<script>\s*// Theme toggle logic\s*document\.addEventListener\(.*?</script>',
        '',
        html, flags=re.DOTALL, count=1
    )

    # Insert sidebar include after <body>
    html = inject_sidebar_include_after_body(html)

    # Wrap container
    html = wrap_content(html, '    <div class="container">')

    return html


def migrate_no_sidebar(html, container_selector='<div class="container">'):
    """
    For templates that have no sidebar (coaches, leaves, settings, backups).
    Just add the include, wrap content.
    """
    html = inject_css_link(html)
    html = inject_sidebar_include_after_body(html)
    html = wrap_content(html, container_selector)
    return html


def migrate_weekoff_leaves(html):
    """weekoff_leaves.html — main content is in <div class="page">."""
    html = inject_css_link(html)
    html = inject_sidebar_include_after_body(html)
    html = wrap_content(html, '    <div class="page">')
    return html


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

migrations = {
    'dashboard.html':            migrate_dashboard,
    'tasks.html':                migrate_tasks,
    'analytics_ai.html':         lambda h: migrate_grid_layout(
                                     h, 'analyticsSidebar', 'analyticsLayout'),
    'summer_camp_incentives.html': migrate_summer_camp,
    'centers_list.html':         migrate_centers_list,
    'coaches.html':              migrate_no_sidebar,
    'leaves.html':               migrate_no_sidebar,
    'settings.html':             migrate_no_sidebar,
    'backups.html':              migrate_no_sidebar,
    'weekoff_leaves.html':       migrate_weekoff_leaves,
}

print('Starting sidebar migration...\n')
errors = []
for filename, fn in migrations.items():
    path = os.path.join(TEMPLATES, filename)
    if not os.path.exists(path):
        print(f'  ⚠ NOT FOUND: {filename}')
        continue
    try:
        original = read(path)
        updated  = fn(original)
        if updated != original:
            write(path, updated)
        else:
            print(f'  — no changes needed: {filename}')
    except Exception as e:
        errors.append((filename, e))
        print(f'  ✗ ERROR in {filename}: {e}')

if errors:
    print(f'\n{len(errors)} error(s) occurred.')
else:
    print('\nAll migrations completed successfully.')
