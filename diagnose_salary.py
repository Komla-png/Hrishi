"""Diagnostic script to check salary data."""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'academy.db')

def diagnose_salary():
    """Check salary data and active coaches."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Check total active coaches
    active_coaches = cur.execute("""
        SELECT COUNT(*) as count FROM coaches
        WHERE end_month IS NULL AND end_year IS NULL
    """).fetchone()
    print(f"✅ Active coaches (no end date): {active_coaches['count']}")
    
    # Check total inactive coaches
    inactive_coaches = cur.execute("""
        SELECT COUNT(*) as count FROM coaches
        WHERE end_month IS NOT NULL OR end_year IS NOT NULL
    """).fetchone()
    print(f"❌ Inactive coaches (with end date): {inactive_coaches['count']}")
    
    # Check total salary records for 2026
    total_salary_records = cur.execute("""
        SELECT COUNT(*) as count FROM coach_salaries WHERE year = 2026
    """).fetchone()
    print(f"💰 Total salary records for 2026: {total_salary_records['count']}")
    
    # Check salary sum for active coaches only
    active_salary = cur.execute("""
        SELECT COALESCE(SUM(cs.salary), 0) as total
        FROM coach_salaries cs
        JOIN coaches co ON cs.coach_id = co.id
        WHERE cs.year = 2026 AND co.end_month IS NULL AND co.end_year IS NULL
    """).fetchone()
    print(f"💵 Total salary (active coaches only): ₹{active_salary['total']:.2f}")
    
    # Check salary sum for ALL coaches
    all_salary = cur.execute("""
        SELECT COALESCE(SUM(salary), 0) as total
        FROM coach_salaries
        WHERE year = 2026
    """).fetchone()
    print(f"💵 Total salary (ALL coaches): ₹{all_salary['total']:.2f}")
    
    # Check if coaches have multiple salary entries per month
    duplicates = cur.execute("""
        SELECT coach_id, month, COUNT(*) as count
        FROM coach_salaries
        WHERE year = 2026
        GROUP BY coach_id, month
        HAVING count > 1
    """).fetchall()
    
    print(f"\n⚠️  Salary entries with duplicates per coach/month: {len(duplicates)}")
    if duplicates:
        for dup in duplicates[:5]:
            print(f"    Coach {dup['coach_id']}, Month {dup['month']}: {dup['count']} records")
    
    # Check if a coach appears in multiple centers
    multi_center_coaches = cur.execute("""
        SELECT name, COUNT(DISTINCT center_id) as center_count, GROUP_CONCAT(center_id) as centers
        FROM coaches
        WHERE end_month IS NULL AND end_year IS NULL
        GROUP BY name
        HAVING center_count > 1
    """).fetchall()
    
    print(f"\n👥 Coaches in multiple centers: {len(multi_center_coaches)}")
    if multi_center_coaches:
        for coach in multi_center_coaches[:5]:
            print(f"    {coach['name']}: Centers {coach['centers']}")
    
    conn.close()

if __name__ == '__main__':
    diagnose_salary()
