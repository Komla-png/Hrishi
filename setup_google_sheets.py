"""Backward-compatible setup entrypoint.

This command now runs Excel sync validation.
"""

from setup_excel_sync import main


if __name__ == "__main__":
    main()
