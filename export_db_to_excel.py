"""Export current project database data to Excel sync workbook.

This creates/overwrites the workbook used by excel_sync.py so all existing
project data is available for editing in Excel.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from openpyxl import Workbook


load_dotenv()


def _db_path() -> str:
    return os.environ.get("DATABASE_PATH", "instance/academy.db").strip()


def _excel_path() -> str:
    return os.environ.get("EXCEL_SYNC_FILE", "instance/dashboard_sync.xlsx").strip()


def export() -> None:
    db_path = _db_path()
    excel_path = _excel_path()

    if not os.path.exists(db_path):
        raise RuntimeError(f"Database file not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Pull monthly rows with center names.
    monthly_rows = cur.execute(
        """
        SELECT c.name AS center_name,
               md.month,
               md.year,
               md.revenue,
               md.target
        FROM monthly_data md
        JOIN centers c ON md.center_id = c.id
        ORDER BY c.name COLLATE NOCASE, md.year, md.month
        """
    ).fetchall()

    # Pull coach salary rows with center/coach names and optional end date fields.
    coach_rows = cur.execute(
        """
        SELECT c.name AS center_name,
               co.name AS coach_name,
               cs.month,
               cs.year,
               cs.salary,
               co.end_month,
               co.end_year
        FROM coach_salaries cs
        JOIN coaches co ON cs.coach_id = co.id
        JOIN centers c ON co.center_id = c.id
        ORDER BY c.name COLLATE NOCASE, co.name COLLATE NOCASE, cs.year, cs.month
        """
    ).fetchall()

    conn.close()

    out_path = Path(excel_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()

    ws_monthly = wb.active
    ws_monthly.title = "MonthlyData"
    ws_monthly.append(["center_name", "month", "year", "revenue", "target"])
    for row in monthly_rows:
        ws_monthly.append(
            [
                row["center_name"],
                row["month"],
                row["year"],
                float(row["revenue"] or 0),
                float(row["target"] or 0),
            ]
        )

    ws_coach = wb.create_sheet(title="CoachSalaries")
    ws_coach.append(["center_name", "coach_name", "month", "year", "salary", "end_month", "end_year"])
    for row in coach_rows:
        ws_coach.append(
            [
                row["center_name"],
                row["coach_name"],
                row["month"],
                row["year"],
                float(row["salary"] or 0),
                row["end_month"] or "",
                row["end_year"] or "",
            ]
        )

    wb.save(out_path)
    print(f"Exported monthly rows: {len(monthly_rows)}")
    print(f"Exported coach salary rows: {len(coach_rows)}")
    print(f"Excel file updated: {out_path}")


if __name__ == "__main__":
    export()
