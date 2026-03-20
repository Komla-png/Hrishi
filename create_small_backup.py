import os
import zipfile

# Folders/files to exclude from backup
EXCLUDE = [
    'backups', 'project_backups', '__pycache__', '.venv', 'instance/logs', 'instance/uploads',
    '*.pyc', '*.pyo', '*.db', '*.sqlite3', '*.log', '*.zip', '*.tar', '*.gz', '*.rar', '*.7z',
    '.git', '.DS_Store', 'node_modules', 'env', 'venv', '.env', '.idea', '.vscode',
]

# Maximum allowed backup size in bytes (25MB)
MAX_SIZE = 25 * 1024 * 1024

# Output backup file name
OUTPUT_ZIP = 'project_backup_under_25MB.zip'


def should_exclude(path):
    for pattern in EXCLUDE:
        if pattern.startswith('*'):
            if path.endswith(pattern[1:]):
                return True
        elif pattern in path:
            return True
    return False


def zipdir(path, ziph):
    for root, dirs, files in os.walk(path):
        # Exclude directories
        dirs[:] = [d for d in dirs if not should_exclude(os.path.join(root, d))]
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, path)
            if not should_exclude(rel_path):
                ziph.write(file_path, rel_path)


def create_backup():
    with zipfile.ZipFile(OUTPUT_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipdir('.', zipf)
    size = os.path.getsize(OUTPUT_ZIP)
    if size > MAX_SIZE:
        print(f"Backup too large: {size/1024/1024:.2f} MB. Please exclude more files.")
    else:
        print(f"Backup created: {OUTPUT_ZIP} ({size/1024/1024:.2f} MB)")


if __name__ == '__main__':
    create_backup()
