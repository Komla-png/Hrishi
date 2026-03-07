"""Check exact salary for Jan-March 2026."""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'academy.db')

def verify_salary():
    """Check exact salary calculation."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    months = ['January', 'February', 'March']
    
    print("Salary Breakdown (Jan-March 2026):\n")
    
    # Check with ACTIVE coaches only
    print("=== ACTIVE COACHES ONLY ===")
    total_active = 0
    for month in months:
        result = cur.execute("""
            SELECT COALESCE(SUM(cs.salary), 0) as total
            FROM coach_salaries cs
            JOIN coaches co ON cs.coach_id = co.id
            WHERE cs.year = 2026 AND cs.month = ? 
            AND co.end_month IS NULL AND co.end_year IS NULL
        """, (month,)).fetchone()
        print(f"{month:<12}: ₹{result['total']:>10,.0f}")
        total_active += result['total']
    
    print(f"{'TOTAL':<12}: ₹{total_active:>10,.0f}")
    
    # Check ALL coaches (including inactive)
    print("\n=== ALL COACHES (including inactive) ===")
    total_all = 0
    for month in months:
        result = cur.execute("""
            SELECT COALESCE(SUM(salary), 0) as total
            FROM coach_salaries
            WHERE year = 2026 AND month = ?
        """, (month,)).fetchone()
        print(f"{month:<12}: ₹{result['total']:>10,.0f}")
        total_all += result['total']
    
    print(f"{'TOTAL':<12}: ₹{total_all:>10,.0f}")
    
    # Calculate percentage
    revenue = cur.execute("""
        SELECT COALESCE(SUM(revenue), 0) as total
        FROM monthly_data
        WHERE year = 2026 AND month IN ('January', 'February', 'March')
    """).fetchone()
    
    print(f"\n📊 Revenue (Jan-Mar): ₹{revenue['total']:,.0f}")
    print(f"💵 Salary (Active, Jan-Mar): ₹{total_active:,.0f}")
    print(f"💵 Salary (All, Jan-Mar): ₹{total_all:,.0f}")
    print(f"📈 Percentage (Active): {total_active/revenue['total']*100:.1f}%")
    print(f"📈 Percentage (All): {total_all/revenue['total']*100:.1f}%")
    
    conn.close()

if __name__ == '__main__':
    verify_salary()
