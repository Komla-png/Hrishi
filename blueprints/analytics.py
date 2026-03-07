"""Analytics blueprint - Executive analytics and performance insights."""

from datetime import datetime
from flask import Blueprint, render_template, request

from utils import get_db, login_required, CALENDAR_MONTHS

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/analytics')
@login_required
def analytics():
    """Render analytics page with revenue, target, salary and achievement insights."""
    year = int(request.args.get('year', datetime.now().year))
    current_month = datetime.now().strftime('%B')
    
    # Get month range filters from query params
    from_month = request.args.get('from_month', 'January')
    to_month = request.args.get('to_month', current_month)
    
    # Calculate included months based on filters
    try:
        from_index = CALENDAR_MONTHS.index(from_month)
        to_index = CALENDAR_MONTHS.index(to_month)
        
        # Ensure from is before to
        if from_index > to_index:
            from_index, to_index = to_index, from_index
            
        included_months = CALENDAR_MONTHS[from_index:to_index + 1]
    except ValueError:
        # Fallback to Jan-to-current if invalid months provided
        current_month_index = CALENDAR_MONTHS.index(current_month) if current_month in CALENDAR_MONTHS else len(CALENDAR_MONTHS) - 1
        included_months = CALENDAR_MONTHS[:current_month_index + 1]
        from_month = 'January'
        to_month = current_month

    conn = get_db()
    cur = conn.cursor()

    monthly_rows = cur.execute(
        """
        SELECT month,
               COALESCE(SUM(revenue), 0) AS total_revenue,
               COALESCE(SUM(target), 0) AS total_target
        FROM monthly_data
        WHERE year = ? AND month IN ({})
        GROUP BY month
        """.format(','.join('?' * len(included_months))),
        (year, *included_months),
    ).fetchall()

    monthly_totals = {
        row['month']: {
            'revenue': float(row['total_revenue'] or 0),
            'target': float(row['total_target'] or 0),
        }
        for row in monthly_rows
    }

    salary_rows = cur.execute(
        """
        SELECT co.center_id,
               cs.month,
               COALESCE(SUM(cs.salary), 0) AS total_salary
        FROM coach_salaries cs
        JOIN coaches co ON cs.coach_id = co.id
        WHERE cs.year = ? 
          AND co.end_month IS NULL 
          AND co.end_year IS NULL
          AND cs.month IN ({})
        GROUP BY co.center_id, cs.month
        """.format(','.join('?' * len(included_months))),
        (year, *included_months),
    ).fetchall()

    salary_by_center_month = {
        (row['center_id'], row['month']): float(row['total_salary'] or 0)
        for row in salary_rows
    }

    salary_by_center = {}
    for row in salary_rows:
        cid = row['center_id']
        salary_by_center[cid] = salary_by_center.get(cid, 0.0) + float(row['total_salary'] or 0)

    center_rows = cur.execute(
        """
        SELECT c.id,
               c.name,
               COALESCE(SUM(md.revenue), 0) AS total_revenue,
               COALESCE(SUM(md.target), 0) AS total_target
        FROM centers c
        LEFT JOIN monthly_data md ON md.center_id = c.id AND md.year = ? AND md.month IN ({})
        GROUP BY c.id, c.name
        ORDER BY c.name COLLATE NOCASE
        """.format(','.join('?' * len(included_months))),
        (year, *included_months),
    ).fetchall()

    centers = []
    for row in center_rows:
        cid = row['id']
        revenue = float(row['total_revenue'] or 0)
        target = float(row['total_target'] or 0)
        salary = float(salary_by_center.get(cid, 0))

        achievement = (revenue / target * 100) if target > 0 else 0
        salary_percent = (salary / revenue * 100) if revenue > 0 else 0

        centers.append(
            {
                'id': cid,
                'name': row['name'],
                'revenue': round(revenue, 2),
                'target': round(target, 2),
                'salary': round(salary, 2),
                'achievement': round(achievement, 1),
                'salary_percent': round(salary_percent, 1),
            }
        )

    total_revenue = round(sum(c['revenue'] for c in centers), 2)
    total_target = round(sum(c['target'] for c in centers), 2)
    total_salary = round(sum(c['salary'] for c in centers), 2)
    achievement_pct = round((total_revenue / total_target * 100) if total_target > 0 else 0, 1)

    avg_salary_pct = round((total_salary / total_revenue * 100) if total_revenue > 0 else 0, 1)

    ranked_centers = sorted(centers, key=lambda x: x['achievement'], reverse=True)
    best_center = ranked_centers[0]['name'] if ranked_centers else 'N/A'

    monthly_revenue = []
    monthly_target = []
    monthly_achievement = []
    monthly_growth = []

    # For the first month, try to get previous month's revenue for growth calculation
    previous_revenue = None
    if included_months:
        first_month = included_months[0]
        first_month_index = CALENDAR_MONTHS.index(first_month)
        
        # If first month is not January, get previous month from same year
        if first_month_index > 0:
            prev_month = CALENDAR_MONTHS[first_month_index - 1]
            prev_year = year
        else:
            # If first month is January, get December from previous year
            prev_month = 'December'
            prev_year = year - 1
        
        # Try to get previous month's revenue
        prev_row = cur.execute(
            """
            SELECT COALESCE(SUM(revenue), 0) AS total_revenue
            FROM monthly_data
            WHERE year = ? AND month = ?
            """,
            (prev_year, prev_month),
        ).fetchone()
        
        if prev_row and prev_row['total_revenue'] > 0:
            previous_revenue = float(prev_row['total_revenue'])
    
    for month in included_months:
        month_revenue = round(monthly_totals.get(month, {}).get('revenue', 0), 2)
        month_target = round(monthly_totals.get(month, {}).get('target', 0), 2)
        month_achievement_pct = round((month_revenue / month_target * 100) if month_target > 0 else 0, 1)

        monthly_revenue.append(month_revenue)
        monthly_target.append(month_target)
        monthly_achievement.append(month_achievement_pct)

        if previous_revenue is None or previous_revenue == 0:
            monthly_growth.append(None)
        else:
            monthly_growth.append(round(((month_revenue - previous_revenue) / previous_revenue) * 100, 1))
        previous_revenue = month_revenue

    heatmap_rows = []
    salary_monitoring_series = []
    for c in centers:
        cid = c['id']
        month_achievements = []
        month_salary_pct = []

        for month in included_months:
            cur.execute(
                """
                SELECT COALESCE(SUM(revenue), 0) AS revenue,
                       COALESCE(SUM(target), 0) AS target
                FROM monthly_data
                WHERE center_id = ? AND year = ? AND month = ?
                """,
                (cid, year, month),
            )
            md = cur.fetchone()
            month_revenue = float(md['revenue'] or 0)
            month_target = float(md['target'] or 0)
            month_salary = salary_by_center_month.get((cid, month), 0)

            month_ach = round((month_revenue / month_target * 100) if month_target > 0 else 0, 1)
            month_sal_pct = round((month_salary / month_revenue * 100) if month_revenue > 0 else 0, 1)

            month_achievements.append(month_ach)
            month_salary_pct.append(month_sal_pct)

        heatmap_rows.append({'center': c['name'], 'values': month_achievements})
        salary_monitoring_series.append({'center': c['name'], 'values': month_salary_pct})

    distribution_bins = {
        '<60%': 0,
        '60-79%': 0,
        '80-99%': 0,
        '100-119%': 0,
        '>=120%': 0,
    }

    for c in centers:
        ach = c['achievement']
        if ach < 60:
            distribution_bins['<60%'] += 1
        elif ach < 80:
            distribution_bins['60-79%'] += 1
        elif ach < 100:
            distribution_bins['80-99%'] += 1
        elif ach < 120:
            distribution_bins['100-119%'] += 1
        else:
            distribution_bins['>=120%'] += 1

    alerts = []
    for c in ranked_centers:
        reasons = []
        if c['achievement'] < 80:
            reasons.append(f"Achievement only {c['achievement']}%")
        if c['salary_percent'] > 30:
            reasons.append(f"Salary % high at {c['salary_percent']}%")
        if reasons:
            alerts.append({'center': c['name'], 'severity': 'high' if c['achievement'] < 60 else 'medium', 'message': ' | '.join(reasons)})

    conn.close()

    summary = {
        'total_revenue': total_revenue,
        'total_target': total_target,
        'achievement_pct': achievement_pct,
        'avg_salary_pct': avg_salary_pct,
        'best_center': best_center,
        'total_salary': total_salary,
    }

    return render_template(
        'analytics.html',
        year=year,
        from_month=from_month,
        to_month=to_month,
        all_months=CALENDAR_MONTHS,
        months=included_months,
        summary=summary,
        ranked_centers=ranked_centers,
        monthly_revenue=monthly_revenue,
        monthly_target=monthly_target,
        monthly_achievement=monthly_achievement,
        monthly_growth=monthly_growth,
        heatmap_rows=heatmap_rows,
        salary_monitoring_series=salary_monitoring_series,
        distribution_bins=distribution_bins,
        alerts=alerts,
    )
