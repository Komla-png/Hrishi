$filePath = 'c:\Users\HZ902\OneDrive\Desktop\academy_dashboard\project_backups\backup_2026-02-22_full\templates\analytics.html'

# Read the file
$lines = Get-Content $filePath

# Find the topbar section and replace it
$inTopbar = $false
$newLines = @()
$i = 0

while ($i -lt $lines.Length) {
    $line = $lines[$i]
    
    if ($line -match '^\s*<div class="topbar"') {
        # Start of topbar - add the new version
        $newLines += '        <div class="topbar">'
        $newLines += '            <div>'
        $newLines += '                <h1 class="title">Executive Analytics</h1>'
        $newLines += '                <p class="subtitle">Revenue, target, achievement and salary efficiency analytics for {{ year }} ({{ from_month[:3] }} - {{ to_month[:3] }})</p>'
        $newLines += '            </div>'
        $newLines += '            <div style="display:flex;gap:8px;align-items:center;">'
        $newLines += '                <select class="year-select" id="yearSelect" onchange="updateFilters()">'
        $newLines += '                    {% for y in range(2023, 2031) %}<option value="{{ y }}" {% if y == year %}selected{% endif %}>{{ y }}</option>{% endfor %}'
        $newLines += '                </select>'
        $newLines += '                <select class="year-select" id="fromMonth" onchange="updateFilters()" style="width:auto;">'
        $newLines += '                    {% for m in all_months %}<option value="{{ m }}" {% if m == from_month %}selected{% endif %}>{{ m[:3] }}</option>{% endfor %}'
        $newLines += '                </select>'
        $newLines += '                <span style="color:#9ca3af;">to</span>'
        $newLines += '                <select class="year-select" id="toMonth" onchange="updateFilters()" style="width:auto;">'
        $newLines += '                    {% for m in all_months %}<option value="{{ m }}" {% if m == to_month %}selected{% endif %}>{{ m[:3] }}</option>{% endfor %}'
        $newLines += '                </select>'
        $newLines += '            </div>'
        $newLines += '        </div>'
        $newLines += '        <script>'
        $newLines += '        function updateFilters() {'
        $newLines += '            const year = document.getElementById(''yearSelect'').value;'
        $newLines += '            const fromMonth = document.getElementById(''fromMonth'').value;'
        $newLines += '            const toMonth = document.getElementById(''toMonth'').value;'
        $newLines += '            window.location.href = `/analytics?year=${year}&from_month=${fromMonth}&to_month=${toMonth}`;'
        $newLines += '        }'
        $newLines += '        </script>'
        
        # Skip lines until we find the closing </div>
        $i++
        while ($i -lt $lines.Length -and $lines[$i] -notmatch '^\s*</div>\s*$') {
            $i++
        }
        # Skip the closing </div>
        $i++
        # Skip blank line if there is one
        if ($i -lt $lines.Length -and $lines[$i] -match '^\s*$') {
            $newLines += ''
            $i++
        }
    } else {
        $newLines += $line
        $i++
    }
}

# Write the modified content
$newLines | Set-Content $filePath

Write-Host "Template updated successfully!" -ForegroundColor Green
Write-Host "Total lines: $($newLines.Length)" -ForegroundColor Cyan
