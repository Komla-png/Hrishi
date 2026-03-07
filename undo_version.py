import os
import shutil
from datetime import datetime

BACKUP_DIR = 'backups/version_undo'
TARGET_DIR = '.'  # Project root

# List of files to backup/restore (customize as needed)
FILES_TO_TRACK = [
    'app.py',
    'models.py',
    'models_center.py',
    'models_coach_salary.py',
    'utils.py',
    'blueprints/analytics.py',
    'blueprints/auth.py',
    'blueprints/coaches.py',
    'blueprints/dashboard.py',
    'blueprints/leaves.py',
    'blueprints/settings.py',
    'templates/dashboard.html',
    'templates/analytics.html',
    'templates/coaches.html',
    'templates/leaves.html',
    'templates/settings.html',
]

def backup_current_version():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    for rel_path in FILES_TO_TRACK:
        src = os.path.join(TARGET_DIR, rel_path)
        dst = os.path.join(BACKUP_DIR, rel_path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(src):
            shutil.copy2(src, dst)
    print(f"Backup complete. Files saved to {BACKUP_DIR}")

def restore_previous_version():
    for rel_path in FILES_TO_TRACK:
        backup_file = os.path.join(BACKUP_DIR, rel_path)
        target_file = os.path.join(TARGET_DIR, rel_path)
        if os.path.exists(backup_file):
            shutil.copy2(backup_file, target_file)
    print("Restore complete. Project files reverted to previous backup.")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Backup or restore project files for undo functionality.')
    parser.add_argument('action', choices=['backup', 'restore'], help='backup: Save current version. restore: Undo to previous version.')
    args = parser.parse_args()

    if args.action == 'backup':
        backup_current_version()
    elif args.action == 'restore':
        restore_previous_version()
