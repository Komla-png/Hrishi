import os
import sys
import zipfile
import shutil

# Usage: python restore_project.py path/to/backup.zip

def restore_backup(backup_zip):
    project_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(project_dir, 'temp_restore')

    # Clean up any previous temp restore
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)

    # Extract backup zip to temp directory
    with zipfile.ZipFile(backup_zip, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    # Copy all files from temp_dir to project_dir (overwrite)
    for root, dirs, files in os.walk(temp_dir):
        rel_path = os.path.relpath(root, temp_dir)
        dest_path = os.path.join(project_dir, rel_path) if rel_path != '.' else project_dir
        os.makedirs(dest_path, exist_ok=True)
        for file in files:
            src_file = os.path.join(root, file)
            dst_file = os.path.join(dest_path, file)
            shutil.copy2(src_file, dst_file)

    # Clean up temp directory
    shutil.rmtree(temp_dir)
    print(f'Restore complete! Project restored from {backup_zip}')

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python restore_project.py path/to/backup.zip')
        sys.exit(1)
    restore_backup(sys.argv[1])
