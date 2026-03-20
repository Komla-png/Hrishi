"""Coaches blueprint - Coach management and salary routes."""

import calendar
import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect

from models_coach_salary import calculate_final_salary_for_month, count_lop_leave_days_for_month
from utils import get_db, login_required, CALENDAR_MONTHS, create_backup

coaches_bp = Blueprint('coaches', __name__)


@coaches_bp.route("/coaches", methods=["GET", "POST"])
@login_required
def coaches():
    """Manage coaches and their salaries."""
    conn = get_db()
    cur = conn.cursor()
    month = request.args.get("month", datetime.now().strftime("%B"))
    year = int(request.args.get("year", datetime.now().year))
    selected_center = request.args.get("center")
    if selected_center:
        selected_center = int(selected_center)
    
    if request.method == "POST":
        action = request.form.get("action")
        
        # Auto-backup before any data modification
        create_backup("auto_coaches")
        
        if action == "add_coach":
            _add_coach(cur, request.form, month, year)
            conn.commit()

        elif action == "add_coach_bulk":
            _add_coach_bulk(cur, request.form, month, year)
            conn.commit()
            
        elif action == "update_salary":
            _update_salary(cur, request.form, year)
            conn.commit()
            
        elif action == "edit_coach":
            _edit_coach(cur, request.form)
            conn.commit()
        
        return redirect(f"/coaches?month={month}&year={year}")

    # Get all coaches with their current month salary - only for centers in this month
    cur.execute("""
        SELECT c.id, c.name, c.center_id, 
               COALESCE(cs.salary, 0) as salary
        FROM coaches c
        LEFT JOIN coach_salaries cs ON c.id = cs.coach_id AND cs.month = ? AND cs.year = ?
        WHERE c.center_id IN (
            SELECT DISTINCT center_id FROM monthly_data WHERE month = ? AND year = ?
        )
    """, (month, year, month, year))
    coaches_rows = cur.fetchall()
    coaches_list = []
    for row in coaches_rows:
        salary_info = calculate_final_salary_for_month(
            cur,
            coach_id=row["id"],
            year=year,
            month_name=month,
            monthly_salary=float(row["salary"] or 0),
        )
        coach = dict(row)
        coach["salary"] = salary_info["final_salary"]
        coach["salary_deduction"] = salary_info["deduction"]
        coach["lop_leave_days"] = salary_info["lop_leave_days"]
        coaches_list.append(coach)
    
    # Only show centers that have data for this month
    cur.execute("""
        SELECT * FROM centers 
        WHERE id IN (SELECT DISTINCT center_id FROM monthly_data WHERE month = ? AND year = ?)
    """, (month, year))
    centers = cur.fetchall()
    salary_by_coach = _get_salary_by_coach(cur, year)
    monthly_salary = _get_monthly_salary(cur, year)

    conn.close()

    return render_template(
        "coaches.html",
        coaches=coaches_list,
        centers=centers,
        month=month,
        year=year,
        monthly_salary=monthly_salary,
        calendar_months=CALENDAR_MONTHS,
        salary_by_coach=salary_by_coach,
        selected_center=selected_center,
    )


def _add_coach(cur, form, month, year):
    """Add a new coach - prevent duplicates."""
    name = form["name"].strip()
    center_id = form["center_id"]
    initial_salary = float(form.get("salary") or 0)
    
    # Check if coach with this name already exists in this center
    cur.execute("""
        SELECT id FROM coaches WHERE center_id = ? AND name = ?
    """, (center_id, name))
    existing = cur.fetchone()

    coach_id = None
    if not existing:
        # Only insert if coach doesn't exist
        cur.execute("""
            INSERT INTO coaches(name, center_id)
            VALUES(?,?)
        """, (name, center_id))
        coach_id = cur.lastrowid
    else:
        coach_id = existing["id"]

    if coach_id and initial_salary > 0:
        _update_salary(
            cur,
            {
                "coach_id": str(coach_id),
                "salary_month": month,
                "salary_year": str(year),
                "salary": str(initial_salary),
            },
            year,
        )


def _add_coach_bulk(cur, form, month, year):
    """Add multiple coaches from parsed JSON payload. Invalid entries are skipped."""
    center_id = form.get("center_id")
    if not center_id:
        return

    payload = form.get("bulk_payload") or ""
    if not payload.strip():
        return

    try:
        entries = json.loads(payload)
    except (TypeError, ValueError):
        return

    if not isinstance(entries, list):
        return

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        name = str(entry.get("name") or "").strip()
        if not name:
            continue

        try:
            salary = float(entry.get("salary") or 0)
        except (TypeError, ValueError):
            continue

        if salary < 0:
            continue

        _add_coach(
            cur,
            {
                "name": name,
                "center_id": center_id,
                "salary": str(salary),
            },
            month,
            year,
        )


def _edit_coach(cur, form):
    """Edit coach name, center, and end date."""
    coach_id = form.get("coach_id")
    end_month = form.get("end_month")
    end_year = form.get("end_year")
    cur.execute("""
        UPDATE coaches SET name=?, center_id=?, end_month=?, end_year=?
        WHERE id=?
    """, (form["name"], form["center_id"], end_month, end_year, coach_id))


def _net_to_gross_for_month(cur, coach_id, year, month_name, desired_final_salary):
    """Convert desired final (after LOP deduction) salary into storable gross salary."""
    desired_final_salary = float(desired_final_salary or 0)
    if desired_final_salary <= 0:
        return 0.0

    month_number = CALENDAR_MONTHS.index(month_name) + 1
    total_days_in_month = calendar.monthrange(year, month_number)[1]
    if total_days_in_month <= 0:
        return round(desired_final_salary, 2)

    lop_leave_days = count_lop_leave_days_for_month(cur, coach_id, year, month_name)
    deduction_ratio = lop_leave_days / total_days_in_month

    # If all payable days are consumed by LOP, keep a safe fallback value.
    if deduction_ratio >= 1:
        return round(desired_final_salary, 2)

    gross_salary = desired_final_salary / (1 - deduction_ratio)
    return round(gross_salary, 2)


def _update_salary(cur, form, year):
    """Update salary for a coach and auto-update targets."""
    coach_id = int(form.get("coach_id"))
    salary_month = form.get("salary_month")
    salary_year = int(form.get("salary_year", year))
    desired_final_salary = float(form.get("salary") or 0)
    
    # Sync salary for all months in the year
    from utils import CALENDAR_MONTHS
    # Get coach's end_month and end_year
    cur.execute("SELECT end_month, end_year FROM coaches WHERE id=?", (coach_id,))
    row = cur.fetchone()
    end_month = row[0] if row else None
    end_year = row[1] if row else None
    from utils import CALENDAR_MONTHS
    # Sync salary (any value) from selected month to all following months, previous months unchanged
    start_idx = CALENDAR_MONTHS.index(salary_month)
    for idx, m in enumerate(CALENDAR_MONTHS):
        if idx >= start_idx:
            set_salary = _net_to_gross_for_month(
                cur,
                coach_id=coach_id,
                year=salary_year,
                month_name=m,
                desired_final_salary=desired_final_salary,
            )
            # If end_year is set and this year > end_year, salary is 0
            if end_year and salary_year > end_year:
                set_salary = 0
            # If end_year is set and this year == end_year and month is after end_month, salary is 0
            if end_year and salary_year == end_year and end_month and CALENDAR_MONTHS.index(m) > CALENDAR_MONTHS.index(end_month):
                set_salary = 0
            
            # Use INSERT OR REPLACE to prevent duplicates
            cur.execute("""
                INSERT OR REPLACE INTO coach_salaries(coach_id, month, year, salary)
                VALUES(?,?,?,?)
            """, (coach_id, m, salary_year, set_salary))
    
    # Auto-update target based on total salary for the center
    cur.execute("SELECT center_id FROM coaches WHERE id=?", (coach_id,))
    coach_row = cur.fetchone()
    if coach_row:
        center_id = coach_row["center_id"]
        _update_center_targets(cur, center_id, salary_year)


def _update_center_targets(cur, center_id, year):
    """Update targets for months that already have data for this center."""
    # Only update months that already exist for this center (don't create new entries)
    cur.execute("""
        SELECT DISTINCT month FROM monthly_data 
        WHERE center_id=? AND year=?
    """, (center_id, year))
    existing_months = [row["month"] for row in cur.fetchall()]
    
    for m in existing_months:
        cur.execute("""
            SELECT cs.coach_id, COALESCE(cs.salary, 0) as salary
            FROM coach_salaries cs
            JOIN coaches co ON cs.coach_id = co.id
            WHERE co.center_id=? AND cs.month=? AND cs.year=?
        """, (center_id, m, year))
        salary_rows = cur.fetchall()
        total_salary = 0
        for row in salary_rows:
            salary_info = calculate_final_salary_for_month(
                cur,
                coach_id=row["coach_id"],
                year=year,
                month_name=m,
                monthly_salary=float(row["salary"] or 0),
            )
            total_salary += salary_info["final_salary"]
        
        # Calculate target (salary should be <= 29.9% of target)
        calc_target = round(total_salary / 0.299, 2) if total_salary > 0 else 0
        
        if calc_target > 0:
            cur.execute("""
                UPDATE monthly_data SET target=?
                WHERE center_id=? AND month=? AND year=?
            """, (calc_target, center_id, m, year))


def _get_salary_by_coach(cur, year):
    """Build LOP-adjusted salary lookup by coach and month."""
    cur.execute("""
        SELECT coach_id, month, salary FROM coach_salaries WHERE year=?
    """, (year,))
    all_salaries = cur.fetchall()
    
    salary_by_coach = {}
    for row in all_salaries:
        cid = row["coach_id"]
        month_name = row["month"]
        salary_info = calculate_final_salary_for_month(
            cur,
            coach_id=cid,
            year=year,
            month_name=month_name,
            monthly_salary=float(row["salary"] or 0),
        )
        if cid not in salary_by_coach:
            salary_by_coach[cid] = {}
        salary_by_coach[cid][month_name] = salary_info["final_salary"]
    
    return salary_by_coach


def _get_monthly_salary(cur, year):
    """Get total salary per month - only for existing coaches with valid centers."""
    cur.execute("""
        SELECT cs.coach_id, cs.month, COALESCE(cs.salary, 0) AS salary
        FROM coach_salaries cs
        JOIN coaches c ON cs.coach_id = c.id
        JOIN centers ct ON c.center_id = ct.id
        WHERE cs.year=?
    """, (year,))
    sal_rows = cur.fetchall()

    salary_by_month = {month: 0 for month in CALENDAR_MONTHS}
    for row in sal_rows:
        month_name = row["month"]
        if month_name not in salary_by_month:
            continue
        salary_info = calculate_final_salary_for_month(
            cur,
            coach_id=row["coach_id"],
            year=year,
            month_name=month_name,
            monthly_salary=float(row["salary"] or 0),
        )
        salary_by_month[month_name] += salary_info["final_salary"]

    monthly_salary = []
    for m in CALENDAR_MONTHS:
        total_salary = salary_by_month.get(m, 0) or 0
        monthly_salary.append({
            "month": m,
            "total_salary": round(total_salary, 2),
        })
    
    return monthly_salary


@coaches_bp.route("/delete_coach/<int:coach_id>")
@login_required
def delete_coach(coach_id):
    """Delete a coach and their salary records."""
    month = request.args.get("month", datetime.now().strftime("%B"))
    year = request.args.get("year", datetime.now().year)
    
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("DELETE FROM coach_salaries WHERE coach_id=?", (coach_id,))
    cur.execute("DELETE FROM coaches WHERE id=?", (coach_id,))
    conn.commit()
    conn.close()
    
    return redirect(f"/coaches?month={month}&year={year}")
