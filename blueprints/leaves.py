"""Leaves blueprint - Coach leave management and tracking."""

from collections import defaultdict
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, jsonify

from utils import get_db, login_required, CALENDAR_MONTHS, create_backup

leaves_bp = Blueprint('leaves', __name__)

# Leave types
LEAVE_TYPES = ['Paid', 'LOP', 'OT']

LEAVE_TYPE_ALIASES = {
    'paid': 'Paid',
    'unpaid': 'LOP',
    'lop': 'LOP',
    'loss of pay': 'LOP',
    'loss_of_pay': 'LOP',
    'lossofpay': 'LOP',
    'ot': 'OT',
}

LEAVE_DURATION_OPTIONS = {'full_day', 'half_day'}


def build_calendar_month_series(monthly_leaves=None):
    """Return monthly leave totals in fixed Jan-Dec order with zero-filled gaps."""
    source = monthly_leaves or {}
    ordered = {}
    for month in CALENDAR_MONTHS:
        ordered[month] = round(float(source.get(month, 0) or 0), 1)
    return ordered


def calculate_days(from_date_str, to_date_str):
    """Calculate number of days between two dates (inclusive)."""
    try:
        from_date = datetime.strptime(from_date_str, '%Y-%m-%d')
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d')
        return (to_date - from_date).days + 1
    except:
        return 1


def normalize_leave_type(raw_leave_type):
    """Map user-submitted leave types to canonical values used across the app."""
    value = (raw_leave_type or '').strip()
    if not value:
        return 'Paid'

    normalized_key = value.lower().replace('_', ' ')
    normalized_key = ' '.join(normalized_key.split())
    normalized_value = LEAVE_TYPE_ALIASES.get(normalized_key, value.title())
    if normalized_value not in LEAVE_TYPES:
        return 'Paid'
    return normalized_value


def normalize_leave_duration(raw_duration):
    """Restrict duration values to supported options."""
    value = (raw_duration or 'full_day').strip().lower()
    return value if value in LEAVE_DURATION_OPTIONS else 'full_day'


def get_leave_year(from_date_str):
    """Store the leave year from the selected from_date instead of trusting hidden form data."""
    try:
        return datetime.strptime(from_date_str, '%Y-%m-%d').year
    except (TypeError, ValueError):
        return datetime.now().year


def _fetch_filtered_leaves(
    cur,
    year,
    selected_month='All',
    selected_coach='',
    selected_coach_search='',
    selected_center='',
    selected_duration='All',
):
    """Fetch leave rows using the same filter rules used by the leaves page."""
    query = """
        SELECT cl.id, cl.coach_id, c.name as coach_name, ct.name as center_name,
               cl.from_date, cl.to_date, cl.leave_type, cl.leave_duration, cl.remarks, cl.created_at,
               ROUND((julianday(cl.to_date) - julianday(cl.from_date) + 1) -
                     CASE WHEN cl.leave_duration = 'half_day' THEN 0.5 ELSE 0 END, 1) as days
        FROM coach_leaves cl
        JOIN coaches c ON cl.coach_id = c.id
        JOIN centers ct ON c.center_id = ct.id
        WHERE cl.year = ?
          AND lower(replace(replace(coalesce(cl.leave_type, ''), ' ', ''), '_', '')) != 'weekoff'
    """
    params = [year]

    if selected_month and selected_month != 'All' and selected_month in CALENDAR_MONTHS:
        query += " AND strftime('%m', cl.from_date) = ?"
        month_num = str(CALENDAR_MONTHS.index(selected_month) + 1).zfill(2)
        params.append(month_num)

    if selected_coach:
        try:
            params.append(int(selected_coach))
            query += " AND cl.coach_id = ?"
        except (TypeError, ValueError):
            pass

    if selected_coach_search:
        query += " AND lower(c.name) LIKE ?"
        params.append(f"%{selected_coach_search.lower()}%")

    if selected_center:
        try:
            params.append(int(selected_center))
            query += " AND c.center_id = ?"
        except (TypeError, ValueError):
            pass

    if selected_duration and selected_duration != 'All':
        query += " AND cl.leave_duration = ?"
        params.append(selected_duration)

    query += " ORDER BY cl.from_date DESC"
    cur.execute(query, params)
    return cur.fetchall()


def _leave_type_key(value):
    """Normalize leave type labels for grouping logic."""
    return (value or '').strip().lower().replace(' ', '').replace('_', '')


def _build_filtered_snapshot(leaves_list):
    """Build summary cards, coach stats, and chart series from filtered leaves rows."""
    monthly_leaves = {month: 0.0 for month in CALENDAR_MONTHS}
    type_totals = defaultdict(float)
    coach_summary_map = defaultdict(
        lambda: {
            'coach_name': '',
            'center_name': '',
            'lop_days': 0.0,
            'approved_days': 0.0,
            'total_days': 0.0,
            'ot_days': 0.0,
        }
    )

    total_leave_days = 0.0
    total_lop_days = 0.0
    total_ot_days = 0.0

    for row in leaves_list:
        coach_id = row[1]
        coach_name = row[2] or ''
        center_name = row[3] or ''
        from_date = row[4]
        leave_type = row[6] or ''
        days = float(row[10] or 0)
        key = _leave_type_key(leave_type)

        if key in {'weekoff'}:
            continue

        type_totals[leave_type] += days

        if from_date:
            try:
                month_index = int(str(from_date)[5:7]) - 1
                if 0 <= month_index < len(CALENDAR_MONTHS):
                    monthly_leaves[CALENDAR_MONTHS[month_index]] += days
            except (TypeError, ValueError):
                pass

        coach_entry = coach_summary_map[coach_id]
        coach_entry['coach_name'] = coach_name
        coach_entry['center_name'] = center_name

        if key in {'ot'}:
            coach_entry['ot_days'] += days
            total_ot_days += days
            continue

        coach_entry['total_days'] += days
        total_leave_days += days
        if key in {'lop', 'lossofpay', 'unpaid'}:
            coach_entry['lop_days'] += days
            total_lop_days += days
        else:
            coach_entry['approved_days'] += days

    total_approved_days = max(total_leave_days - total_lop_days, 0.0)
    coach_summary = sorted(
        coach_summary_map.values(),
        key=lambda row: row['total_days'],
        reverse=True,
    )
    leave_type_stats = sorted(type_totals.items(), key=lambda row: row[1], reverse=True)

    return {
        'summary': {
            'total_leave_days': round(total_leave_days, 1),
            'total_lop_days': round(total_lop_days, 1),
            'total_approved_days': round(total_approved_days, 1),
            'total_ot_days': round(total_ot_days, 1),
        },
        'coach_summary': [
            {
                'coach_name': row['coach_name'],
                'center_name': row['center_name'],
                'lop_days': round(row['lop_days'], 1),
                'approved_days': round(row['approved_days'], 1),
                'total_days': round(row['total_days'], 1),
                'ot_days': round(row['ot_days'], 1),
            }
            for row in coach_summary
        ],
        'monthly_leaves': build_calendar_month_series(monthly_leaves),
        'leave_type_stats': [[leave_type, round(days, 1)] for leave_type, days in leave_type_stats],
    }


@leaves_bp.route("/leaves", methods=["GET", "POST"])
@login_required
def leaves():
    """Manage coach leaves."""
    conn = get_db()
    cur = conn.cursor()
    
    year = int(request.args.get("year", datetime.now().year))
    selected_month = request.args.get("month", "All")
    selected_coach = request.args.get("coach", "")
    selected_coach_search = (request.args.get("coach_search") or "").strip()
    selected_center = request.args.get("center", "")
    selected_duration = request.args.get("duration", "All")
    
    if request.method == "POST":
        action = request.form.get("action")
        
        # Auto-backup before any data modification
        create_backup("auto_leaves")
        
        if action == "add_leave":
            _add_leave(cur, request.form)
            conn.commit()
            
        elif action == "edit_leave":
            _edit_leave(cur, request.form)
            conn.commit()
            
        elif action == "delete_leave":
            leave_id = request.form.get("leave_id")
            cur.execute("DELETE FROM coach_leaves WHERE id=?", (leave_id,))
            conn.commit()
        
        # Preserve filters in redirect
        return redirect(f"/leaves?year={year}&month={selected_month}&coach={selected_coach}&coach_search={selected_coach_search}&center={selected_center}&duration={selected_duration}")

    leaves_list = _fetch_filtered_leaves(
        cur,
        year=year,
        selected_month=selected_month,
        selected_coach=selected_coach,
        selected_coach_search=selected_coach_search,
        selected_center=selected_center,
        selected_duration=selected_duration,
    )
    
    # Get all coaches for dropdown
    cur.execute("""
        SELECT c.id, c.name, ct.name as center_name 
        FROM coaches c 
        JOIN centers ct ON c.center_id = ct.id
        ORDER BY ct.name, c.name
    """)
    coaches_list = cur.fetchall()
    
    # Get all centers for dropdown
    centers = cur.execute("SELECT * FROM centers ORDER BY name").fetchall()
    
        # Get leave statistics per coach for the year (excluding Week Off from all leave management outputs)
    cur.execute("""
        SELECT c.id, c.name, ct.name as center_name, 
               COUNT(cl.id) as total_leaves,
                             SUM(CASE WHEN lower(replace(replace(coalesce(cl.leave_type, ''), ' ', ''), '_', '')) IN ('lop', 'lossofpay', 'unpaid') THEN (julianday(cl.to_date) - julianday(cl.from_date) + 1) - CASE WHEN cl.leave_duration = 'half_day' THEN 0.5 ELSE 0 END ELSE 0 END) as lop_days,
                             SUM(CASE WHEN lower(replace(replace(coalesce(cl.leave_type, ''), ' ', ''), '_', '')) NOT IN ('lop', 'lossofpay', 'unpaid', 'weekoff', 'ot') THEN (julianday(cl.to_date) - julianday(cl.from_date) + 1) - CASE WHEN cl.leave_duration = 'half_day' THEN 0.5 ELSE 0 END ELSE 0 END) as approved_days,
                             SUM(CASE WHEN lower(replace(replace(coalesce(cl.leave_type, ''), ' ', ''), '_', '')) NOT IN ('weekoff', 'ot') THEN (julianday(cl.to_date) - julianday(cl.from_date) + 1) - CASE WHEN cl.leave_duration = 'half_day' THEN 0.5 ELSE 0 END ELSE 0 END) as total_days,
                             SUM(CASE WHEN lower(replace(replace(coalesce(cl.leave_type, ''), ' ', ''), '_', '')) = 'ot' THEN (julianday(cl.to_date) - julianday(cl.from_date) + 1) - CASE WHEN cl.leave_duration = 'half_day' THEN 0.5 ELSE 0 END ELSE 0 END) as ot_days
        FROM coaches c
        JOIN centers ct ON c.center_id = ct.id
        LEFT JOIN coach_leaves cl ON c.id = cl.coach_id AND cl.year = ?
        GROUP BY c.id
        ORDER BY total_days DESC
    """, (year,))
    leave_stats = cur.fetchall()
    
    # Get monthly leave count for chart (sum of days, not records)
    monthly_leaves = {}
    for month in CALENDAR_MONTHS:
        month_num = str(CALENDAR_MONTHS.index(month) + 1).zfill(2)
        cur.execute("""
            SELECT COALESCE(SUM((julianday(to_date) - julianday(from_date) + 1) * CASE WHEN leave_duration = 'half_day' THEN 0.5 ELSE 1 END), 0) 
            FROM coach_leaves 
                        WHERE year = ? AND strftime('%m', from_date) = ?
                            AND lower(replace(replace(coalesce(leave_type, ''), ' ', ''), '_', '')) != 'weekoff'
        """, (year, month_num))
        monthly_leaves[month] = float(cur.fetchone()[0] or 0)
    monthly_leaves = build_calendar_month_series(monthly_leaves)
    
    # Get leave type breakdown (with total days)
    cur.execute("""
        SELECT leave_type, 
             ROUND(SUM((julianday(to_date) - julianday(from_date) + 1) * CASE WHEN leave_duration = 'half_day' THEN 0.5 ELSE 1 END), 1) as total_days
        FROM coach_leaves 
        WHERE year = ?
          AND lower(replace(replace(coalesce(leave_type, ''), ' ', ''), '_', '')) != 'weekoff'
        GROUP BY leave_type
        ORDER BY total_days DESC
    """, (year,))
    leave_type_stats = [list(row) for row in cur.fetchall()]
    
    # Get total leave days and LOP days for the year (excluding Week Off from leave management)
    cur.execute("""
        SELECT 
            COALESCE(SUM(CASE WHEN lower(replace(replace(coalesce(leave_type, ''), ' ', ''), '_', '')) NOT IN ('weekoff', 'ot') THEN (julianday(to_date) - julianday(from_date) + 1) * CASE WHEN leave_duration = 'half_day' THEN 0.5 ELSE 1 END ELSE 0 END), 0) as total_days,
            COALESCE(SUM(CASE WHEN lower(replace(replace(coalesce(leave_type, ''), ' ', ''), '_', '')) IN ('lop', 'lossofpay', 'unpaid') THEN (julianday(to_date) - julianday(from_date) + 1) * CASE WHEN leave_duration = 'half_day' THEN 0.5 ELSE 1 END ELSE 0 END), 0) as lop_days,
            COALESCE(SUM(CASE WHEN lower(replace(replace(coalesce(leave_type, ''), ' ', ''), '_', '')) = 'ot' THEN (julianday(to_date) - julianday(from_date) + 1) * CASE WHEN leave_duration = 'half_day' THEN 0.5 ELSE 1 END ELSE 0 END), 0) as ot_days
        FROM coach_leaves 
        WHERE year = ?
          AND lower(replace(replace(coalesce(leave_type, ''), ' ', ''), '_', '')) != 'weekoff'
    """, (year,))
    totals = cur.fetchone()
    total_leave_days = float(totals[0] or 0)
    total_lop_days = float(totals[1] or 0)
    total_ot_days = float(totals[2] or 0)
    
    conn.close()

    return render_template(
        "leaves.html",
        leaves=leaves_list,
        coaches=coaches_list,
        centers=centers,
        year=year,
        selected_month=selected_month,
        selected_coach=selected_coach,
        selected_coach_search=selected_coach_search,
        selected_center=selected_center,
        selected_duration=selected_duration,
        calendar_months=CALENDAR_MONTHS,
        leave_types=LEAVE_TYPES,
        leave_stats=leave_stats,
        monthly_leaves=monthly_leaves,
        leave_type_stats=leave_type_stats,
        total_leave_days=total_leave_days,
        total_lop_days=total_lop_days,
        total_ot_days=total_ot_days,
    )


@leaves_bp.route('/leaves/search')
@login_required
def leaves_search():
    """Return filtered leave records for async table updates."""
    raw_year = request.args.get('year', datetime.now().year)
    try:
        year = int(raw_year)
    except (TypeError, ValueError):
        year = datetime.now().year

    selected_month = request.args.get('month', 'All')
    selected_coach = request.args.get('coach', '')
    selected_center = request.args.get('center', '')
    selected_duration = request.args.get('duration', 'All')
    selected_coach_search = (request.args.get('coach_name') or '').strip()

    conn = get_db()
    cur = conn.cursor()
    leaves_list = _fetch_filtered_leaves(
        cur,
        year=year,
        selected_month=selected_month,
        selected_coach=selected_coach,
        selected_coach_search=selected_coach_search,
        selected_center=selected_center,
        selected_duration=selected_duration,
    )
    snapshot = _build_filtered_snapshot(leaves_list)
    conn.close()

    return jsonify(
        {
            'ok': True,
            'count': len(leaves_list),
            'records': [
                {
                    'id': row[0],
                    'coach_id': row[1],
                    'coach_name': row[2],
                    'center_name': row[3],
                    'from_date': row[4],
                    'to_date': row[5],
                    'leave_type': row[6],
                    'leave_duration': row[7],
                    'remarks': row[8] or '',
                    'created_at': row[9],
                    'days': float(row[10] or 0),
                }
                for row in leaves_list
            ],
            'summary': snapshot['summary'],
            'coach_summary': snapshot['coach_summary'],
            'monthly_leaves': snapshot['monthly_leaves'],
            'leave_type_stats': snapshot['leave_type_stats'],
        }
    )


def _add_leave(cur, form):
    """Add a new leave record. Check for duplicates first."""
    coach_id = form.get("coach_id")
    from_date = form.get("from_date")
    to_date = form.get("to_date") or from_date  # Default to same date if not provided
    leave_type = normalize_leave_type(form.get("leave_type", "Paid"))
    leave_duration = normalize_leave_duration(form.get("leave_duration", "full_day"))
    remarks = form.get("remarks", "").strip()
    year = get_leave_year(from_date)
    
    # Check for existing leave with same dates for this coach
    cur.execute("""
        SELECT id FROM coach_leaves 
        WHERE coach_id=? AND from_date=? AND to_date=?
    """, (coach_id, from_date, to_date))
    
    existing = cur.fetchone()
    if not existing:
        # Only insert if no exact duplicate exists
        cur.execute("""
            INSERT INTO coach_leaves(coach_id, from_date, to_date, leave_type, leave_duration, remarks, year)
            VALUES(?, ?, ?, ?, ?, ?, ?)
        """, (coach_id, from_date, to_date, leave_type, leave_duration, remarks, year))


def _edit_leave(cur, form):
    """Edit an existing leave record."""
    leave_id = form.get("leave_id")
    coach_id = form.get("coach_id")
    from_date = form.get("from_date")
    to_date = form.get("to_date") or from_date
    leave_type = normalize_leave_type(form.get("leave_type", "Paid"))
    leave_duration = normalize_leave_duration(form.get("leave_duration", "full_day"))
    remarks = form.get("remarks", "").strip()
    year = get_leave_year(from_date)
    
    cur.execute("""
        UPDATE coach_leaves 
        SET coach_id=?, from_date=?, to_date=?, leave_type=?, leave_duration=?, remarks=?, year=?
        WHERE id=?
    """, (coach_id, from_date, to_date, leave_type, leave_duration, remarks, year, leave_id))
