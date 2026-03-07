"""Check monthly salary breakdown."""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'academy.db')

def check_monthly():
    """Check salary and revenue by month."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    months = ['January', 'February', 'March', 'April', 'May', 'June', 
              'July', 'August', 'September', 'October', 'November', 'December']
    
    print("Monthly Breakdown for 2026:\n")
    print(f"{'Month':<12} | {'Revenue':>12} | {'Salary':>12} | {'Salary %':>10}")
    print("-" * 55)
    
    total_revenue = 0
    total_salary = 0
    
    for month in months:
        # Get revenue for month
        revenue = cur.execute("""
            SELECT COALESCE(SUM(revenue), 0) as total
            FROM monthly_data
            WHERE year = 2026 AND month = ?
        """, (month,)).fetchone()
        
        # Get salary for month (active coaches only)
        salary = cur.execute("""
            SELECT COALESCE(SUM(cs.salary), 0) as total
            FROM coach_salaries cs
            JOIN coaches co ON cs.coach_id = co.id
            WHERE cs.year = 2026 AND cs.month = ? 
            AND co.end_month IS NULL AND co.end_year IS NULL
        """, (month,)).fetchone()
        
        rev = revenue['total']
        sal = salary['total']
        pct = (sal / rev * 100) if rev > 0 else 0
        
        if rev > 0 or sal > 0:
            print(f"{month:<12} | ₹{rev:>11,.0f} | ₹{sal:>11,.0f} | {pct:>9.1f}%")
            total_revenue += rev
            total_salary += sal
    
    print("-" * 55)
    overall_pct = (total_salary / total_revenue * 100) if total_revenue > 0 else 0
    print(f"{'TOTAL':<12} | ₹{total_revenue:>11,.0f} | ₹{total_salary:>11,.0f} | {overall_pct:>9.1f}%")
    
    print(f"\n✅ Overall Salary Percentage: {overall_pct:.1f}%")
    
    conn.close()

if __name__ == '__main__':
    check_monthly()
