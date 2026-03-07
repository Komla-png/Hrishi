$filePath = 'c:\Users\HZ902\OneDrive\Desktop\academy_dashboard\project_backups\backup_2026-02-22_full\templates\analytics.html'
$content = Get-Content $filePath -Raw

# Replace the topbar section
$oldPattern = @'
        <div class="topbar">
            <div>
                <h1 class="title">Executive Analytics</h1>
                <p class="subtitle">Revenue, target, achievement and salary efficiency analytics for {{ year }}</p>
            </div>
            <select class="year-select" onchange="window.location.href='/analytics?year='+this.value">
                {% for y in range(2023, 2031) %}<option value="{{ y }}" {% if y == year %}selected{% endif %}>{{ y }}</option>{% endfor %}
            </select>
        </div>

        <section class="cards">
'@

$newPattern = @'
        <div class="topbar">
            <div>
                <h1 class="title">Executive Analytics</h1>
                <p class="subtitle">Revenue, target, achievement and salary efficiency analytics for {{ year }} ({{ from_month[:3] }} - {{ to_month[:3] }})</p>
            </div>
            <div style="display:flex;gap:8px;align-items:center;">
                <select class="year-select" id="yearSelect" onchange="updateFilters()">
                    {% for y in range(2023, 2031) %}<option value="{{ y }}" {% if y == year %}selected{% endif %}>{{ y }}</option>{% endfor %}
                </select>
                <select class="year-select" id="fromMonth" onchange="updateFilters()" style="width:auto;">
                    {% for m in all_months %}<option value="{{ m }}" {% if m == from_month %}selected{% endif %}>{{ m[:3] }}</option>{% endfor %}
                </select>
                <span style="color:#9ca3af;">to</span>
                <select class="year-select" id="toMonth" onchange="updateFilters()" style="width:auto;">
                    {% for m in all_months %}<option value="{{ m }}" {% if m == to_month %}selected{% endif %}>{{ m[:3] }}</option>{% endfor %}
                </select>
            </div>
        </div>
        <script>
        function updateFilters() {
            const year = document.getElementById('yearSelect').value;
            const fromMonth = document.getElementById('fromMonth').value;
            const toMonth = document.getElementById('toMonth').value;
            window.location.href = `/analytics?year=${year}&from_month=${fromMonth}&to_month=${toMonth}`;
        }
        </script>

        <section class="cards">
'@

$content = $content.Replace($oldPattern, $newPattern)
$content | Set-Content $filePath -NoNewline

Write-Host "Template updated successfully!" -ForegroundColor Green
