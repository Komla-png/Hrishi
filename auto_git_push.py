import subprocess
import sys
from datetime import datetime

# Customize your commit message here
def get_commit_message():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return f'Auto-commit: {now}'

def run(cmd):
    print(f'Running: {cmd}')
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f'Error running: {cmd}')
        sys.exit(result.returncode)

def main():
    run('git add .')
    run(f'git commit -m "{get_commit_message()}"')
    run('git push origin main')

if __name__ == '__main__':
    main()
