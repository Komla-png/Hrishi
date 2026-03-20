# Google Sheets Sync Setup

## 1. Required Google Sheet Structure

Create one spreadsheet with two worksheets:

### Worksheet: `MonthlyData`

| center_name | month    | year | revenue | target |
|-------------|----------|------|---------|--------|
| Center 1    | January  | 2026 | 120000  | 150000 |
| Center 2    | February | 2026 | 98000   | 125000 |

Required columns:
- `center_name`
- `month` (full month like `January` or short month like `Jan`)
- `year`
- `revenue`
- `target`

### Worksheet: `CoachSalaries` (optional)

| center_name | coach_name | month   | year | salary | end_month | end_year |
|-------------|------------|---------|------|--------|-----------|----------|
| Center 1    | Ravi       | January | 2026 | 22000  |           |          |
| Center 2    | Neha       | January | 2026 | 25000  | December  | 2026     |

Required columns:
- `center_name`
- `coach_name`
- `month`
- `year`
- `salary`

Optional columns:
- `end_month`
- `end_year`

## 2. Environment Variables

Add these values to your `.env`:

```env
DATABASE_PATH=instance/academy.db
# For PostgreSQL instead of SQLite, set DATABASE_URL and leave DATABASE_PATH unused:
# DATABASE_URL=postgresql://user:password@host:5432/dbname

GOOGLE_SERVICE_ACCOUNT_FILE=instance/google_service_account.json
GOOGLE_SPREADSHEET_ID=your_google_spreadsheet_id
GOOGLE_MONTHLY_WORKSHEET=MonthlyData
GOOGLE_COACH_WORKSHEET=CoachSalaries
SHEET_SYNC_INTERVAL_SECONDS=60
```

Both `google_sheets_sync.py` and `run_sheet_sync_scheduler.py` auto-load `.env` using `python-dotenv`.

## 3. Service Account Access

1. Create a Google Cloud service account with Google Sheets API access.
2. Download JSON key file.
3. Save as `instance/google_service_account.json`.
4. Share your Google Sheet with the service account email (Editor access).

## 4. Manual Sync

```bash
python google_sheets_sync.py
```

## 5. Automatic Sync Every Minute

```bash
python run_sheet_sync_scheduler.py
```

This script continuously runs and syncs every `SHEET_SYNC_INTERVAL_SECONDS` (default `60`).

## 6. Database Driver Notes

- SQLite is used when `DATABASE_PATH` is set and `DATABASE_URL` is empty.
- PostgreSQL is used when `DATABASE_URL` starts with `postgresql://` (via `pg8000`).

## 7. Safety and Validation Behavior

- Rows with missing `center_name`, invalid `month`, or invalid `year` are skipped.
- Invalid numeric values default to `0` only where safely parseable.
- Successful rows are upserted (insert or update existing records).
- Sync is transactional: if DB write fails, that cycle is rolled back.
