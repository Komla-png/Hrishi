# Duplicate Prevention System - Complete Documentation

## Overview
A comprehensive duplicate prevention and removal system has been implemented across the Academy Dashboard application to prevent duplicate entries and clean up existing duplicates.

## Changes Made

### 1. **Database Schema Updates** (`app.py`)

#### Added Unique Constraints
- **monthly_data**: `UNIQUE(center_id, month, year)` - Ensures one entry per center per month per year
- **coach_salaries**: `UNIQUE(coach_id, month, year)` - Ensures one salary record per coach per month per year  
- **coach_leaves**: `UNIQUE(coach_id, from_date, to_date)` - Ensures one leave record per coach per date range

#### Automatic Duplicate Cleaning
- Added `_clean_duplicates()` function called during app startup
- Automatically removes duplicate entries from all tables
- Keeps the entry with the lowest ID (first occurrence)
- Logs cleaned duplicates count to console

```python
# Console output example on startup:
# 🧹 Cleaned duplicates: monthly_data(2), coach_salaries(1), coach_leaves(0)
```

### 2. **Coaches Module** (`blueprints/coaches.py`)

#### Change: Salary Update
- Changed from separate SELECT + INSERT/UPDATE to `INSERT OR REPLACE`
- This ensures only one salary record exists per coach/month/year combination
- Prevents accidental duplicate entries when updating salaries

**Before:**
```python
cur.execute("SELECT id FROM coach_salaries WHERE ...")
existing = cur.fetchone()
if existing:
    cur.execute("UPDATE coach_salaries SET ...")
else:
    cur.execute("INSERT INTO coach_salaries ...")
```

**After:**
```python
cur.execute("INSERT OR REPLACE INTO coach_salaries ...")
```

### 3. **Leaves Module** (`blueprints/leaves.py`)

#### Change: Leave Entry Validation
- Added duplicate check before inserting leave records
- Prevents identical leave entries for the same coach and date range
- Compares coach_id, from_date, and to_date

**New Logic:**
```python
def _add_leave(cur, form):
    # ... get form data ...
    
    # Check for existing leave with same dates
    cur.execute("""
        SELECT id FROM coach_leaves 
        WHERE coach_id=? AND from_date=? AND to_date=?
    """, (coach_id, from_date, to_date))
    
    existing = cur.fetchone()
    if not existing:
        # Only insert if no exact duplicate exists
        cur.execute("INSERT INTO coach_leaves ...")
```

### 4. **Task Tracker** (`blueprints/tracker.py`)

#### Change 1: Load Tasks Function
- Added duplicate detection when loading JSON tasks
- Maintains a set of seen task IDs
- Returns only unique tasks (first occurrence of each ID)

#### Change 2: Add Task Function
- Added duplicate check before creating new task
- Prevents adding tasks with identical name, frequency, and date
- Only inserts if no matching task exists

**Duplicate Detection Logic:**
```python
existing_task = next((t for t in tasks 
                     if t['name'] == name 
                     and t['frequency'] == frequency 
                     and t.get('date') == task_date), None)

if not existing_task:
    # Create new task
    tasks.append(new_task)
```

### 5. **Duplicate Removal Script** (`remove_monthly_duplicates.py`)

#### Complete Rewrite
- Now handles ALL tables, not just monthly_data
- Improved documentation and console output
- Can be run manually to clean existing duplicates

**Features:**
- Removes duplicates from `monthly_data`
- Removes duplicates from `coach_salaries`
- Removes duplicates from `coach_leaves`
- Reports count of entries deleted from each table
- Keeps entries with lowest ID (first occurrence)

**Usage:**
```bash
python remove_monthly_duplicates.py
```

**Sample Output:**
```
🧹 Starting duplicate removal process...
✅ Deleted 2 duplicate entries from monthly_data
✅ Deleted 1 duplicate entries from coach_salaries
✅ No duplicates found in coach_leaves

🎉 Duplicate removal complete! Total deleted: 3
```

## How It Works

### Three-Layer Protection System

#### Layer 1: Prevention (Application Level)
- Duplicate checks before INSERT operations
- `INSERT OR REPLACE` statements automatically replace existing records
- Application-level validation for JSON tasks

#### Layer 2: Database Constraints (Structural Level)
- UNIQUE indexes prevent duplicate entries at the database level
- Enforced automatically by SQLite
- Prevents duplicate entries even if application logic fails

#### Layer 3: Cleanup (Maintenance Level)
- Automatic cleanup on app startup (`_clean_duplicates()`)
- Manual cleanup script (`remove_monthly_duplicates.py`)
- Removes any duplicates that existed before constraints were added

## Duplicate Detection Rules

### For each table:

| Table | Duplicate Criteria | Action |
|-------|-------------------|--------|
| `monthly_data` | Same center_id, month, year | Keep lowest ID, delete others |
| `coach_salaries` | Same coach_id, month, year | Keep lowest ID, delete others |
| `coach_leaves` | Same coach_id, from_date, to_date | Keep lowest ID, delete others |
| `tasks.json` | Same task ID | Keep first occurrence, remove others |
| Add New Task | Same name, frequency, date | Don't add if exists |

## Testing the System

### To verify all duplicates are removed:

```bash
# Run the removal script
python remove_monthly_duplicates.py

# Output will show what was cleaned:
# 🎉 Duplicate removal complete! Total deleted: 0
# (0 means no duplicates found, system is clean)
```

### To verify constraints are working:

1. Try adding the same center/month/year data - should fail or replace
2. Try adding salary for same coach/month/year - should replace
3. Try adding same leave dates - should be prevented
4. Try adding duplicate task - should be prevented

## Future Prevention

Going forward, duplicates will be prevented by:

1. **Database constraints** - UNIQUE indexes prevent duplicates at SQL level
2. **Application checks** - Validation prevents duplicates before INSERT
3. **`INSERT OR REPLACE`** - Replaces existing records if conflict occurs
4. **Automatic startup cleanup** - Any remaining duplicates cleaned on app start

## Maintenance

### Running Maintenance:

```bash
# Manual duplicate removal (monthly recommended)
python remove_monthly_duplicates.py

# Or run during development to verify no duplicates exist
python remove_monthly_duplicates.py
```

### Monitoring:

- Check console output on app startup for cleanup messages
- Monitor database size to ensure duplicates aren't accumulating
- Run removal script weekly during high-activity periods

## Summary of Benefits

✅ **No more duplicate entries** - Three-layer protection system ensures duplicates can't be created  
✅ **Automatic cleanup** - App startup cleans any existing duplicates automatically  
✅ **Better data integrity** - Unique constraints enforce data consistency  
✅ **Cleaner statistics** - No inflated numbers from duplicates  
✅ **Easy maintenance** - Simple script to verify and remove duplicates when needed
