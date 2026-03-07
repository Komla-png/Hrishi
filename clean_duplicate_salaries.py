"""Clean duplicate salary records and keep only one per coach per month per year."""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'academy.db')

def clean_duplicate_salaries():
    """Remove duplicate salary records, keeping the one with highest salary."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Find duplicates
    duplicates = cur.execute("""
        SELECT coach_id, month, year, COUNT(*) as count
        FROM coach_salaries
        GROUP BY coach_id, month, year
        HAVING count > 1
    """).fetchall()
    
    print(f"Found {len(duplicates)} duplicate salary entries")
    
    for dup in duplicates:
        coach_id = dup['coach_id']
        month = dup['month']
        year = dup['year']
        count = dup['count']
        
        # Get all duplicates for this coach/month/year
        records = cur.execute("""
            SELECT id, salary FROM coach_salaries
            WHERE coach_id = ? AND month = ? AND year = ?
            ORDER BY salary DESC
        """, (coach_id, month, year)).fetchall()
        
        print(f"Coach {coach_id}, {month}/{year}: {count} records - keeping highest salary: ₹{records[0]['salary']}")
        
        # Keep the first (highest salary), delete the rest
        for rec in records[1:]:
            cur.execute("DELETE FROM coach_salaries WHERE id = ?", (rec['id'],))
    
    conn.commit()
    conn.close()
    print(f"\n✅ Cleaned {len(duplicates)} duplicate salary entries")

if __name__ == '__main__':
    clean_duplicate_salaries()
