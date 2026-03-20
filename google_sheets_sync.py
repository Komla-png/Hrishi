"""Backward-compatible entrypoint for sheet sync.

This project now uses Excel as the source. The old module name is kept so
existing commands (for example `python google_sheets_sync.py`) continue working.
"""

from excel_sync import main, sync_excel_to_database


# Keep the old callable name to avoid breaking existing imports.
def sync_google_sheets_to_database():
    return sync_excel_to_database()


if __name__ == "__main__":
    main()
