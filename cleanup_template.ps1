$filePath = 'c:\Users\HZ902\OneDrive\Desktop\academy_dashboard\project_backups\backup_2026-02-22_full\templates\analytics.html'

# Read the file with UTF-8 encoding
$content = Get-Content $filePath -Raw -Encoding UTF8

# Remove the leftover old select element
$content = $content -replace '(?s)(\s*</script>\s*)<select class="year-select" onchange="window\.location\.href=''/analytics\?year=''\+this\.value">.*?</select>\s*</div>', '$1'

# Fix rupee symbol if corrupted (? to ₹)
$content = $content -replace '\?{{', '₹{{'

# Write back with UTF-8 encoding
$content | Out-File $filePath -Encoding UTF8 -NoNewline

Write-Host "Template cleaned up successfully!" -ForegroundColor Green
