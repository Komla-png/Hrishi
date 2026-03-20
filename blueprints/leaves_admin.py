from datetime import datetime

from flask import Blueprint, current_app, render_template, redirect, request, flash
from utils import get_db, login_required, create_backup, CALENDAR_MONTHS

leaves_admin_bp = Blueprint('leaves_admin', __name__)

@leaves_admin_bp.route('/leaves/weekoff')
@login_required
def weekoff_leaves():
    current_year = datetime.now().year
    year = request.args.get('year', current_year, type=int)
    selected_month = request.args.get('month', 'All')
    selected_leave_type = request.args.get('leave_type', 'All')
    coach_name = (request.args.get('coach_name') or '').strip()
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()

        # Build filter dropdown values from actual leave data
        cur.execute(
            """
            SELECT DISTINCT leave_type
            FROM coach_leaves
            WHERE leave_type IS NOT NULL AND trim(leave_type) <> ''
            ORDER BY leave_type ASC
            """
        )
        available_leave_types = [row['leave_type'] for row in cur.fetchall()]

        cur.execute(
            """
            SELECT DISTINCT CAST(strftime('%Y', from_date) AS INTEGER) AS year_value
            FROM coach_leaves
            WHERE from_date IS NOT NULL
            ORDER BY year_value DESC
            """
        )
        available_years = [row['year_value'] for row in cur.fetchall() if row['year_value'] is not None]
        if not available_years:
            available_years = list(range(current_year - 3, current_year + 5))

        query = """
            SELECT cl.id,
                   c.name AS coach_name,
                   ct.name AS center_name,
                   cl.from_date AS leave_date,
                   cl.leave_type,
                   strftime('%m', cl.from_date) AS month_num,
                   CAST(strftime('%Y', cl.from_date) AS INTEGER) AS year_value,
                   CASE
                       WHEN lower(coalesce(cl.remarks, '')) LIKE '%reject%' THEN 'Rejected'
                       WHEN lower(coalesce(cl.remarks, '')) LIKE '%pending%' THEN 'Pending'
                       ELSE 'Approved'
                   END AS status
            FROM coach_leaves cl
            JOIN coaches c ON cl.coach_id = c.id
            LEFT JOIN centers ct ON c.center_id = ct.id
            WHERE cl.from_date IS NOT NULL
        """
        params = []

        if year:
            query += " AND CAST(strftime('%Y', cl.from_date) AS INTEGER) = ?"
            params.append(year)

        if selected_month != 'All':
            month_num = str(CALENDAR_MONTHS.index(selected_month) + 1).zfill(2)
            query += " AND strftime('%m', cl.from_date) = ?"
            params.append(month_num)

        if selected_leave_type != 'All':
            query += " AND cl.leave_type = ?"
            params.append(selected_leave_type)

        if coach_name:
            query += " AND lower(c.name) LIKE ?"
            params.append(f"%{coach_name.lower()}%")

        query += " ORDER BY cl.from_date DESC, c.name ASC"
        cur.execute(query, params)
        leave_rows = cur.fetchall()

        leave_records = []
        for row in leave_rows:
            month_name = ''
            try:
                month_idx = int(row['month_num'])
                if 1 <= month_idx <= 12:
                    month_name = CALENDAR_MONTHS[month_idx - 1]
            except (TypeError, ValueError):
                month_name = ''

            leave_records.append({
                'id': row['id'],
                'coach_name': row['coach_name'],
                'leave_type': row['leave_type'],
                'leave_date': row['leave_date'],
                'month': month_name,
                'year': row['year_value'],
                'status': row['status'],
            })

        current_app.logger.info(
            'Leave records query returned %s rows for year=%s month=%s leave_type=%s coach=%s',
            len(leave_records),
            year,
            selected_month,
            selected_leave_type,
            coach_name or '<all>',
        )
        if leave_records:
            current_app.logger.info(
                'Leave records sample rows: %s',
                [
                    {
                        'id': row['id'],
                        'coach_name': row['coach_name'],
                        'leave_type': row['leave_type'],
                    }
                    for row in leave_records[:5]
                ],
            )
        return render_template(
            'weekoff_leaves.html',
            leave_records=leave_records,
            year=year,
            selected_month=selected_month,
            selected_leave_type=selected_leave_type,
            coach_name=coach_name,
            calendar_months=CALENDAR_MONTHS,
            available_years=available_years,
            available_leave_types=available_leave_types,
            error_message=None,
        )
    except Exception as exc:
        current_app.logger.exception('Failed to load /leaves/weekoff for year %s', year)
        if current_app.debug:
            raise
        return render_template(
            'weekoff_leaves.html',
            leave_records=[],
            year=year,
            selected_month=selected_month,
            selected_leave_type=selected_leave_type,
            coach_name=coach_name,
            calendar_months=CALENDAR_MONTHS,
            available_years=list(range(current_year - 3, current_year + 5)),
            available_leave_types=[],
            error_message=str(exc),
        ), 500
    finally:
        if conn is not None:
            conn.close()

# Delete Week Off leave record
@leaves_admin_bp.route('/leaves/weekoff/delete/<int:leave_id>', methods=['POST'])
@login_required
def delete_weekoff_leave(leave_id):
    create_backup('delete_weekoff_leave')
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM coach_leaves WHERE id=?', (leave_id,))
    conn.commit()
    conn.close()
    flash('Week Off leave record deleted!', 'success')
    year = request.form.get('year', datetime.now().year)
    selected_month = request.form.get('month', 'All')
    selected_leave_type = request.form.get('leave_type', 'All')
    coach_name = (request.form.get('coach_name') or '').strip()
    return redirect(f'/leaves/weekoff?year={year}&month={selected_month}&leave_type={selected_leave_type}&coach_name={coach_name}')
