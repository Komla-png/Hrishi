import sqlite3
from utils import get_db

def clear_february_data(year=2026):
    conn = get_db()
    cur = conn.cursor()
    # Delete February data from monthly_data
    cur.execute("DELETE FROM monthly_data WHERE month=? AND year=?", ("February", year))
    # Delete February data from coach_salaries
    cur.execute("DELETE FROM coach_salaries WHERE month=? AND year=?", ("February", year))
    conn.commit()
    conn.close()
    print(f"Cleared all February data for {year}.")

if __name__ == "__main__":
    clear_february_data()