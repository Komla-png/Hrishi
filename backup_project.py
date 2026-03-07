import os
import datetime
import zipfile

# Directory to backup (current project directory)
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(PROJECT_DIR, 'project_backups')

# Ensure backup directory exists
os.makedirs(BACKUP_DIR, exist_ok=True)

def get_backup_filename():
    date_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    return os.path.join(BACKUP_DIR, f'project_backup_{date_str}.zip')

def zipdir(path, ziph):
    # Zip all files and folders in path
    for root, dirs, files in os.walk(path):
        # Skip the backup directory itself
        if BACKUP_DIR in root:
            continue
        for file in files:
            abs_path = os.path.join(root, file)
            rel_path = os.path.relpath(abs_path, path)
            ziph.write(abs_path, rel_path)

def create_backup():
    backup_file = get_backup_filename()
    with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipdir(PROJECT_DIR, zipf)
    print(f'Backup created: {backup_file}')

if __name__ == '__main__':
    create_backup()
