"""
Remove duplicate entries from all database tables.

This script scans all tables for duplicate entries and removes them,
keeping only the first (lowest ID) occurrence of each duplicate set.

Duplicates are detected by checking for identical values in the unique constraint fields:
- monthly_data: center_id, month, year
- coach_salaries: coach_id, month, year
- coach_leaves: coach_id, from_date, to_date
"""

import sqlite3

def remove_duplicates():
    """Remove duplicate entries from all tables."""
    conn = sqlite3.connect('instance/academy.db')
    cur = conn.cursor()
    
    print("🧹 Starting duplicate removal process...")
    
    # Find and delete duplicate rows in monthly_data (keep the lowest id for each group)
    cur.execute('''
        SELECT id FROM monthly_data
        WHERE id NOT IN (
            SELECT MIN(id) FROM monthly_data 
            GROUP BY center_id, month, year
        )
    ''')
    monthly_dup_ids = [row[0] for row in cur.fetchall()]
    
    if monthly_dup_ids:
        cur.executemany('DELETE FROM monthly_data WHERE id=?', [(i,) for i in monthly_dup_ids])
        print(f"✅ Deleted {len(monthly_dup_ids)} duplicate entries from monthly_data")
    else:
        print(f"✅ No duplicates found in monthly_data")
    
    # Find and delete duplicate rows in coach_salaries (keep the lowest id for each group)
    cur.execute('''
        SELECT id FROM coach_salaries
        WHERE id NOT IN (
            SELECT MIN(id) FROM coach_salaries 
            GROUP BY coach_id, month, year
        )
    ''')
    salary_dup_ids = [row[0] for row in cur.fetchall()]
    
    if salary_dup_ids:
        cur.executemany('DELETE FROM coach_salaries WHERE id=?', [(i,) for i in salary_dup_ids])
        print(f"✅ Deleted {len(salary_dup_ids)} duplicate entries from coach_salaries")
    else:
        print(f"✅ No duplicates found in coach_salaries")
    
    # Find and delete duplicate rows in coach_leaves (keep the lowest id for each group)
    cur.execute('''
        SELECT id FROM coach_leaves
        WHERE id NOT IN (
            SELECT MIN(id) FROM coach_leaves 
            GROUP BY coach_id, from_date, to_date
        )
    ''')
    leaves_dup_ids = [row[0] for row in cur.fetchall()]
    
    if leaves_dup_ids:
        cur.executemany('DELETE FROM coach_leaves WHERE id=?', [(i,) for i in leaves_dup_ids])
        print(f"✅ Deleted {len(leaves_dup_ids)} duplicate entries from coach_leaves")
    else:
        print(f"✅ No duplicates found in coach_leaves")
    
    conn.commit()
    conn.close()
    
    total_deleted = len(monthly_dup_ids) + len(salary_dup_ids) + len(leaves_dup_ids)
    print(f"\n🎉 Duplicate removal complete! Total deleted: {total_deleted}")
    return total_deleted

if __name__ == "__main__":
    remove_duplicates()

