# Quick Setup Guide - Complete These Steps

## ✅ What You Need to Do

### Step 1: Get Your Google Sheet ID

1. Open your Google Sheet in a browser
2. Look at the URL - it looks like this:
   ```
   https://docs.google.com/spreadsheets/d/101YPPWtCBHD-qPHb9PaKMxxt1C-SWR80oeXYUOu9MV4/edit
   ```
3. Copy the long ID between `/d/` and `/edit` (example: `1abc123xyz456def789`)

### Step 2: Update .env File

1. Open the `.env` file in your project folder
2. Find the line that says:
   ```
   GOOGLE_SPREADSHEET_ID=
   ```
3. Paste your Sheet ID:
   ```
   GOOGLE_SPREADSHEET_ID=1abc123xyz456def789
   ```
4. Save the file

### Step 3: Create Google Service Account

#### 3a. Go to Google Cloud Console
- Visit: https://console.cloud.google.com
- Sign in with your Google account

#### 3b. Create/Select Project
- Click "Select a project" at the top
- Click "NEW PROJECT"
- Name it (e.g., "Academy Dashboard Sync")
- Click "CREATE"

#### 3c. Enable Google Sheets API
- In the left menu, go to "APIs & Services" → "Library"
- Search for "Google Sheets API"
- Click on it, then click "ENABLE"

#### 3d. Create Service Account
1. Go to "APIs & Services" → "Credentials"
2. Click "CREATE CREDENTIALS" → "Service account"
3. Enter a name (e.g., "sheets-sync")
4. Click "CREATE AND CONTINUE"
5. Skip the optional steps, click "DONE"

#### 3e. Create and Download Key
1. Click on the service account you just created
2. Go to "KEYS" tab
3. Click "ADD KEY" → "Create new key"
4. Choose "JSON" format
5. Click "CREATE"
6. A JSON file will download automatically

#### 3f. Save the Key File
1. Rename the downloaded file to `google_service_account.json`
2. Move it to the `instance` folder in your project:
   ```
   C:\Users\HZ902\OneDrive\Desktop\academy_dashboard\project_backups\backup_2026-02-22_full\instance\google_service_account.json
   ```

### Step 4: Share Your Google Sheet

1. Open the downloaded JSON file
2. Find the `client_email` field - it looks like:
   ```json
   "client_email": "sheets-sync@academy-dashboard-123.iam.gserviceaccount.com"
   ```
3. Copy that email address
4. Open your Google Sheet
5. Click the **Share** button (top-right)
6. Paste the service account email
7. Give it **Editor** permission
8. Click **Send** (uncheck "Notify people" if asked)

---

## 🧪 Test Your Setup

Once you've completed all steps above, run the setup assistant:

```powershell
python setup_google_sheets.py
```

This will validate everything and test the connection.

---

## 🚀 Start Using It

After successful setup:

**One-time manual sync:**
```powershell
python google_sheets_sync.py
```

**Continuous auto-sync (every 60 seconds):**
```powershell
python run_sheet_sync_scheduler.py
```

---

## 📋 Your Google Sheet Structure

Make sure your Google Sheet has these worksheets:

### Worksheet 1: "MonthlyData"
| center_name | month | year | revenue | target |
|-------------|-------|------|---------|--------|
| Center A    | Jan   | 2026 | 50000   | 60000  |
| Center A    | Feb   | 2026 | 55000   | 60000  |

### Worksheet 2: "CoachSalaries"
| center_name | coach_name  | month | year | salary | end_month | end_year |
|-------------|-------------|-------|------|--------|-----------|----------|
| Center A    | John Smith  | Jan   | 2026 | 5000   |           |          |
| Center A    | Jane Doe    | Jan   | 2026 | 4500   |           |          |

**Notes:**
- Month can be "Jan" or "January" (both work)
- `end_month` and `end_year` are optional (leave empty for active coaches)
- All numeric values will be validated

---

## ❓ Need Help?

See the full documentation: `GOOGLE_SHEETS_SYNC_SETUP.md`

Or run the setup assistant for guided help:
```powershell
python setup_google_sheets.py
```
