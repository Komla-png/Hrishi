"""Clean duplicate coaches (same person in multiple centers)."""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'academy.db')

def clean_duplicate_coaches():
    """Remove duplicate coach entries, keeping first one."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Find coaches with same name in multiple centers
    duplicates = cur.execute("""
        SELECT name, GROUP_CONCAT(id) as ids, COUNT(DISTINCT center_id) as center_count
        FROM coaches
        WHERE end_month IS NULL AND end_year IS NULL
        GROUP BY name
        HAVING center_count > 1
    """).fetchall()
    
    print(f"Found {len(duplicates)} duplicate coach entries:\n")
    
    for dup in duplicates:
        ids = [int(x) for x in dup['ids'].split(',')]
        coach_name = dup['name']
        
        # Keep first (lowest ID), delete others
        keep_id = ids[0]
        delete_ids = ids[1:]
        
        # Get salary totals for each duplicate
        for coach_id in ids:
            salary_total = cur.execute(
                "SELECT COALESCE(SUM(salary), 0) as total FROM coach_salaries WHERE coach_id = ? AND year = 2026",
                (coach_id,)
            ).fetchone()
            status = "✅ KEEP" if coach_id == keep_id else "❌ DELETE"
            print(f"  {coach_name} (ID: {coach_id}): ₹{salary_total['total']:.0f} {status}")
        
        # Delete duplicate salary records for coaches we're removing
        for delete_id in delete_ids:
            cur.execute("DELETE FROM coach_salaries WHERE coach_id = ?", (delete_id,))
            cur.execute("DELETE FROM coaches WHERE id = ?", (delete_id,))
        
        print()
    
    conn.commit()
    print(f"✅ Removed {sum(len([int(x) for x in d['ids'].split(',')][1:]) for d in duplicates)} duplicate coach entries")
    conn.close()

if __name__ == '__main__':
    clean_duplicate_coaches()
