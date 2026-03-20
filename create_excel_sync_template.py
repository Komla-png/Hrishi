"""Create a starter Excel workbook for sheet sync.

Generates `instance/dashboard_sync.xlsx` with required worksheets/columns.
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook


OUTPUT_PATH = Path("instance/dashboard_sync.xlsx")


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()

    ws_monthly = wb.active
    ws_monthly.title = "MonthlyData"
    ws_monthly.append(["center_name", "month", "year", "revenue", "target"])
    ws_monthly.append(["Center A", "January", 2026, 50000, 60000])
    ws_monthly.append(["Center A", "February", 2026, 52000, 60000])

    ws_coach = wb.create_sheet(title="CoachSalaries")
    ws_coach.append(["center_name", "coach_name", "month", "year", "salary", "end_month", "end_year"])
    ws_coach.append(["Center A", "John Smith", "January", 2026, 8000, "", ""])
    ws_coach.append(["Center A", "Jane Doe", "February", 2026, 9000, "", ""])

    wb.save(OUTPUT_PATH)
    print(f"Created template: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
