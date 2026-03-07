# Script to ensure all centers have monthly_data for all months of the current year
from app import get_db
from datetime import datetime

def sync_centers_monthly_data(year=None):
    if year is None:
        year = datetime.now().year
    all_months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM centers")
    center_ids = [row[0] for row in cur.fetchall()]
    for center_id in center_ids:
        for m in all_months:
            cur.execute("""
                INSERT OR IGNORE INTO monthly_data(center_id, month, year, revenue, target)
                VALUES(?, ?, ?, 0, 0)
            """, (center_id, m, year))
    conn.commit()
    conn.close()
    print(f"Synced all centers to all months for year {year}.")

if __name__ == "__main__":
    sync_centers_monthly_data()
