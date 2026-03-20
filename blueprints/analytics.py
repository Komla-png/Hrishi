"""Analytics blueprint - Executive analytics and performance insights."""

import csv
import os
import smtplib
from io import BytesIO, StringIO
from datetime import datetime
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape
from flask import Blueprint, jsonify, make_response, render_template, request

from models_coach_salary import calculate_final_salary_for_month
from utils import (
    CALENDAR_MONTHS,
    create_backup,
    get_db,
    login_required,
    sanitize_number,
    validate_csrf,
)

analytics_bp = Blueprint('analytics', __name__)


def _build_report_jpg(year, from_month, to_month, summary, monthly_trend, centers, alerts, ai_items):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return None

    def _load_font(size, bold=False):
        candidates = ['segoeui.ttf', 'arial.ttf', 'tahoma.ttf']
        if bold:
            candidates = ['segoeuib.ttf', 'arialbd.ttf', 'tahomabd.ttf'] + candidates
        for name in candidates:
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                continue
        return ImageFont.load_default()

    def _shorten(text, max_len=68):
        value = str(text or '')
        return value if len(value) <= max_len else value[:max_len - 3] + '...'

    def _to_float(value, default=0.0):
        try:
            return float(str(value).replace('%', '').replace(',', '').strip())
        except (TypeError, ValueError):
            return default

    title_font = _load_font(34, bold=True)
    subtitle_font = _load_font(21)
    section_font = _load_font(24, bold=True)
    label_font = _load_font(16)
    value_font = _load_font(25, bold=True)
    head_font = _load_font(18, bold=True)
    text_font = _load_font(18)
    small_font = _load_font(15)

    trend_rows = list(monthly_trend or [])[:8]
    center_rows = list(centers or [])[:10]
    alert_rows = list(alerts or [])[:6]
    insight_rows = list(ai_items or [])[:5]

    # Match common email body widths to reduce client-side downscaling blur.
    width = 980
    margin = 24
    content_width = width - (margin * 2)
    row_h = 54

    dynamic_height = (
        240 +
        260 +
        100 + max(1, len(trend_rows)) * row_h +
        100 + max(1, len(center_rows)) * row_h +
        90 + max(1, len(alert_rows)) * 54 +
        90 + max(1, len(insight_rows)) * 66 +
        90
    )
    height = max(1300, dynamic_height)

    image = Image.new('RGB', (width, height), '#e2e8f0')
    draw = ImageDraw.Draw(image)

    # Main card and header.
    draw.rectangle((margin, margin, width - margin, height - margin), fill='#f8fafc', outline='#cbd5e1', width=2)
    header_bottom = margin + 170
    draw.rectangle((margin, margin, width - margin, header_bottom), fill='#1e3a8a')
    draw.text((margin + 36, margin + 32), 'Executive Analytics Report', fill='#f8fafc', font=title_font)
    draw.text((margin + 36, margin + 100), f'{year} | {from_month} to {to_month}', fill='#dbeafe', font=subtitle_font)

    y = header_bottom + 24

    scope_center_label = summary.get('scope_center_label') or 'All Centers'
    scope_is_filtered = bool(summary.get('scope_is_filtered'))
    scope_center_match_count = int(summary.get('scope_center_match_count') or 0)
    is_single_center_scope = scope_is_filtered and scope_center_match_count == 1

    # KPI summary section.
    draw.text((margin + 24, y), 'Portfolio Summary', fill='#1e3a8a', font=section_font)
    y += 48
    kpis = [
        ('Total Target', _format_currency(summary.get('total_target', 0))),
        ('Achieved Revenue', _format_currency(summary.get('achieved_revenue', 0))),
        ('Remaining Target', _format_currency(summary.get('remaining_revenue', 0))),
        ('Achievement %', f"{summary.get('achievement_pct', 0)}%"),
        ('Center', _shorten(scope_center_label, 28)) if is_single_center_scope else ('Best Center', _shorten(summary.get('best_center', 'N/A'), 28)),
        ('Average Salary %', f"{summary.get('avg_salary_pct', 0)}%"),
    ]
    card_w = (content_width - 96) // 3
    card_h = 96
    for i, (label, value) in enumerate(kpis):
        r = i // 3
        c = i % 3
        x1 = margin + 24 + c * (card_w + 24)
        y1 = y + r * (card_h + 14)
        x2 = x1 + card_w
        y2 = y1 + card_h
        draw.rectangle((x1, y1, x2, y2), fill='#eef2f7', outline='#d6deea', width=1)
        draw.text((x1 + 12, y1 + 10), label, fill='#64748b', font=label_font)
        value_color = '#15803d' if (label == 'Achievement %' and _to_float(summary.get('achievement_pct', 0)) > 100) else '#0f172a'
        draw.text((x1 + 12, y1 + 44), str(value), fill=value_color, font=value_font)

    y += (card_h * 2) + 28

    def _draw_table(title, headers, rows, right_align=None, col_weights=None, green_if_gt_100_cols=None):
        nonlocal y
        right_align = right_align or set()
        col_weights = col_weights or [1] * len(headers)
        green_if_gt_100_cols = green_if_gt_100_cols or set()
        draw.text((margin + 24, y), title, fill='#1e3a8a', font=section_font)
        y += 44

        x1 = margin + 24
        x2 = width - margin - 24
        header_h = 52
        draw.rectangle((x1, y, x2, y + header_h), fill='#0f172a')

        total_w = x2 - x1
        weight_sum = sum(col_weights) or 1
        col_edges = [x1]
        running = x1
        for weight in col_weights[:-1]:
            running += int(total_w * (weight / weight_sum))
            col_edges.append(running)
        col_edges.append(x2)

        for idx, h in enumerate(headers):
            cell_x1 = col_edges[idx]
            cell_x2 = col_edges[idx + 1]
            text_value = _shorten(h, 18)
            text_w = draw.textlength(text_value, font=head_font)
            tx = int(cell_x1 + ((cell_x2 - cell_x1 - text_w) / 2))
            draw.text((tx, y + 15), text_value, fill='#f8fafc', font=head_font)
            if idx < len(headers) - 1:
                draw.line((cell_x2, y + 6, cell_x2, y + header_h - 6), fill='#1e293b', width=1)
        y += header_h

        if not rows:
            draw.rectangle((x1, y, x2, y + row_h), fill='#f8fafc', outline='#d6deea', width=1)
            draw.text((x1 + 12, y + 14), 'No data available', fill='#64748b', font=text_font)
            y += row_h + 14
            return

        for ridx, row in enumerate(rows):
            bg = '#f8fafc' if ridx % 2 == 0 else '#ffffff'
            draw.rectangle((x1, y, x2, y + row_h), fill=bg, outline='#e2e8f0', width=1)
            for cidx, val in enumerate(row):
                cell_x1 = col_edges[cidx]
                cell_x2 = col_edges[cidx + 1]
                max_len = max(8, int((cell_x2 - cell_x1 - 20) / 10))
                cell_text = _shorten(val, max_len)
                text_bbox = draw.textbbox((0, 0), cell_text, font=text_font)
                text_h = max(1, text_bbox[3] - text_bbox[1])
                ty = int(y + ((row_h - text_h) / 2))
                if cidx in right_align:
                    text_w = draw.textlength(cell_text, font=text_font)
                    tx = int(cell_x2 - text_w - 10)
                else:
                    tx = cell_x1 + 10
                cell_color = '#15803d' if (cidx in green_if_gt_100_cols and _to_float(val, default=-1) > 100) else '#0f172a'
                draw.text((tx, ty), cell_text, fill=cell_color, font=text_font)
                if cidx < len(row) - 1:
                    draw.line((cell_x2, y + 4, cell_x2, y + row_h - 4), fill='#e2e8f0', width=1)
            y += row_h
        y += 14

    _draw_table(
        'Monthly Revenue Trend',
        ['Month', 'Revenue', 'Target', 'Ach %', 'MoM %'],
        [
            [
                str(item.get('month', '')),
                _format_currency(item.get('revenue', 0)),
                _format_currency(item.get('target', 0)),
                f"{item.get('achievement', 0)}%",
                '-' if item.get('growth') is None else f"{item.get('growth', 0):+.1f}%",
            ]
            for item in trend_rows
        ],
        right_align={1, 2, 3, 4},
        col_weights=[1.6, 1.2, 1.2, 0.9, 0.9],
        green_if_gt_100_cols={3},
    )

    _draw_table(
        'Center Snapshot' if is_single_center_scope else 'Center Performance',
        ['Center', 'Revenue', 'Target', 'Ach %', 'Salary %'],
        [
            [
                item.get('name', 'N/A'),
                _format_currency(item.get('revenue', 0)),
                _format_currency(item.get('target', 0)),
                f"{item.get('achievement', 0)}%",
                f"{item.get('salary_percent', 0)}%",
            ]
            for item in center_rows
        ],
        right_align={1, 2, 3, 4},
        col_weights=[1.8, 1.15, 1.15, 0.95, 0.95],
        green_if_gt_100_cols={3},
    )

    # Alerts section.
    draw.text((margin + 24, y), 'Smart Alerts', fill='#1e3a8a', font=section_font)
    y += 44
    if not alert_rows:
        draw.rectangle((margin + 24, y, width - margin - 24, y + 52), fill='#f0fdf4', outline='#bbf7d0', width=1)
        draw.text((margin + 34, y + 14), 'All centers are performing within thresholds.', fill='#15803d', font=text_font)
        y += 66
    else:
        for item in alert_rows:
            is_high = item.get('severity') == 'high'
            bg = '#fef2f2' if is_high else '#fffbeb'
            border = '#dc2626' if is_high else '#f59e0b'
            draw.rectangle((margin + 24, y, width - margin - 24, y + 52), fill=bg, outline=border, width=2)
            msg = f"{item.get('center', 'N/A')}: {item.get('message', '')}"
            draw.text((margin + 34, y + 14), _shorten(msg, 110), fill='#0f172a', font=text_font)
            y += 58

    # AI insights section.
    draw.text((margin + 24, y), 'AI Insights', fill='#1e3a8a', font=section_font)
    y += 44
    if not insight_rows:
        draw.rectangle((margin + 24, y, width - margin - 24, y + 56), fill='#f8fafc', outline='#cbd5e1', width=1)
        draw.text((margin + 34, y + 16), 'No additional AI insights available.', fill='#64748b', font=text_font)
        y += 70
    else:
        for item in insight_rows:
            severity = str(item.get('severity', 'info')).lower()
            if severity == 'high':
                bg, border = '#fef2f2', '#dc2626'
            elif severity == 'medium':
                bg, border = '#fffbeb', '#f59e0b'
            else:
                bg, border = '#f0fdf4', '#22c55e'

            draw.rectangle((margin + 24, y, width - margin - 24, y + 62), fill=bg, outline=border, width=2)
            if is_single_center_scope:
                head = f"{str(item.get('category', '')).replace('_', ' ').title()} [{severity.upper()}]"
            else:
                head = f"#{item.get('rank', '')} {str(item.get('category', '')).replace('_', ' ').title()} [{severity.upper()}]"
            draw.text((margin + 34, y + 8), _shorten(head, 80), fill='#475569', font=small_font)
            draw.text((margin + 34, y + 30), _shorten(item.get('message', ''), 110), fill='#0f172a', font=text_font)
            y += 68

    generated_at = datetime.now().strftime('%d %b %Y %I:%M %p')
    draw.text((margin + 24, height - margin - 34), f'Generated on {generated_at} by Academy Dashboard.', fill='#64748b', font=small_font)

    output = BytesIO()
    image.save(output, format='JPEG', quality=95, optimize=True, subsampling=0)
    return output.getvalue()


SUMMER_CAMP_BASE_TARGETS = {
    'AJ': 377926.42,
    'JC': 267558.53,
    'LeNoah': 150501.67,
    'Maagniv': 170568.56,
    'MBC': 488294.31,
    'Scooled': 418060.20,
    'Sumukha': 382943.14,
    'Tashwin': 110367.89,
}
SUMMER_CAMP_DEFAULT_TARGET_MONTHS = ['April', 'May']


def _normalize_center_name(name):
    return (name or '').strip().lower()


def _sanitize_selected_month(raw_month):
    current_month = datetime.now().strftime('%B')
    return raw_month if raw_month in CALENDAR_MONTHS else current_month


def _sanitize_selected_year(raw_year):
    try:
        return int(raw_year)
    except (TypeError, ValueError):
        return datetime.now().year


def _sanitize_base_target_months(raw_months):
    if raw_months is None:
        candidate_months = list(SUMMER_CAMP_DEFAULT_TARGET_MONTHS)
    elif isinstance(raw_months, str):
        candidate_months = [part.strip() for part in raw_months.split(',') if part and part.strip()]
    elif isinstance(raw_months, (list, tuple, set)):
        candidate_months = [str(part).strip() for part in raw_months if str(part).strip()]
    else:
        candidate_months = list(SUMMER_CAMP_DEFAULT_TARGET_MONTHS)

    valid = []
    seen = set()
    for month in CALENDAR_MONTHS:
        if month in candidate_months and month not in seen:
            valid.append(month)
            seen.add(month)

    return valid or list(SUMMER_CAMP_DEFAULT_TARGET_MONTHS)


def _sanitize_month_range(raw_from_month, raw_to_month):
    current_month = datetime.now().strftime('%B')
    from_month = raw_from_month if raw_from_month in CALENDAR_MONTHS else 'January'
    to_month = raw_to_month if raw_to_month in CALENDAR_MONTHS else current_month

    from_index = CALENDAR_MONTHS.index(from_month)
    to_index = CALENDAR_MONTHS.index(to_month)
    if from_index > to_index:
        from_index, to_index = to_index, from_index
        from_month, to_month = to_month, from_month

    included_months = CALENDAR_MONTHS[from_index:to_index + 1]
    return from_month, to_month, included_months


def _sanitize_month_year_range(raw_start_month, raw_start_year, raw_end_month, raw_end_year):
    current_month = datetime.now().strftime('%B')
    current_year = datetime.now().year

    start_month = raw_start_month if raw_start_month in CALENDAR_MONTHS else 'January'
    end_month = raw_end_month if raw_end_month in CALENDAR_MONTHS else current_month
    start_year = _sanitize_selected_year(raw_start_year)
    end_year = _sanitize_selected_year(raw_end_year)

    start_key = (start_year * 100) + (CALENDAR_MONTHS.index(start_month) + 1)
    end_key = (end_year * 100) + (CALENDAR_MONTHS.index(end_month) + 1)

    if end_key < start_key:
        start_month, end_month = end_month, start_month
        start_year, end_year = end_year, start_year

    included_periods = []
    cursor_year = start_year
    cursor_month_index = CALENDAR_MONTHS.index(start_month)
    end_month_index = CALENDAR_MONTHS.index(end_month)

    while True:
        month_name = CALENDAR_MONTHS[cursor_month_index]
        included_periods.append((month_name, cursor_year))
        if cursor_year == end_year and cursor_month_index == end_month_index:
            break

        cursor_month_index += 1
        if cursor_month_index >= len(CALENDAR_MONTHS):
            cursor_month_index = 0
            cursor_year += 1

        # Safety guard for unexpected edge cases.
        if len(included_periods) > 240:
            break

    if not included_periods:
        included_periods = [(current_month, current_year)]
        start_month = current_month
        end_month = current_month
        start_year = current_year
        end_year = current_year

    return start_month, start_year, end_month, end_year, included_periods


def _parse_recipients(raw_recipients):
    recipients = []
    for recipient in (raw_recipients or '').replace(';', ',').split(','):
        email = recipient.strip()
        if email and email not in recipients:
            recipients.append(email)
    return recipients


def _build_email_summary_snapshot(year, included_months):
    conn = get_db()
    cur = conn.cursor()

    # Monthly totals for trend table
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

    # Salary by center AND month (for AI insights center_month_history)
    salary_rows = cur.execute(
        """
        SELECT co.center_id,
               cs.coach_id,
               cs.month,
               COALESCE(cs.salary, 0) AS salary
        FROM coach_salaries cs
        JOIN coaches co ON cs.coach_id = co.id
        WHERE cs.year = ?
          AND co.end_month IS NULL
          AND co.end_year IS NULL
          AND cs.month IN ({})
        """.format(','.join('?' * len(included_months))),
        (year, *included_months),
    ).fetchall()

    salary_by_center_month = {}
    salary_by_center = {}
    for row in salary_rows:
        cid = row['center_id']
        month_name = row['month']
        salary_info = calculate_final_salary_for_month(
            cur,
            coach_id=row['coach_id'],
            year=year,
            month_name=month_name,
            monthly_salary=float(row['salary'] or 0),
        )
        final_salary = float(salary_info['final_salary'] or 0)
        salary_by_center_month[(cid, month_name)] = salary_by_center_month.get((cid, month_name), 0.0) + final_salary
        salary_by_center[cid] = salary_by_center.get(cid, 0.0) + final_salary

    # Per-center per-month data (for AI insights)
    monthly_center_rows = cur.execute(
        """
        SELECT center_id,
               month,
               COALESCE(SUM(revenue), 0) AS total_revenue,
               COALESCE(SUM(target), 0) AS total_target
        FROM monthly_data
        WHERE year = ? AND month IN ({})
        GROUP BY center_id, month
        """.format(','.join('?' * len(included_months))),
        (year, *included_months),
    ).fetchall()

    monthly_center_totals = {
        (row['center_id'], row['month']): {
            'revenue': float(row['total_revenue'] or 0),
            'target': float(row['total_target'] or 0),
        }
        for row in monthly_center_rows
    }

    # Center totals
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
    center_month_history = {}
    for row in center_rows:
        cid = row['id']
        revenue = float(row['total_revenue'] or 0)
        target = float(row['total_target'] or 0)
        salary = float(salary_by_center.get(cid, 0))
        achievement = (revenue / target * 100) if target > 0 else 0
        salary_percent = (salary / revenue * 100) if revenue > 0 else 0

        center_month_history[cid] = {}
        for month in included_months:
            mt = monthly_center_totals.get((cid, month), {'revenue': 0.0, 'target': 0.0})
            mr = float(mt['revenue'] or 0)
            mt_val = float(mt['target'] or 0)
            ms = salary_by_center_month.get((cid, month), 0.0)
            m_ach = round((mr / mt_val * 100) if mt_val > 0 else 0, 1)
            m_sal_pct = round((ms / mr * 100) if mr > 0 else 0, 1)
            center_month_history[cid][month] = {
                'revenue': round(mr, 2),
                'target': round(mt_val, 2),
                'salary': round(ms, 2),
                'achievement': m_ach,
                'salary_percent': m_sal_pct,
            }

        centers.append({
            'id': cid,
            'name': row['name'],
            'revenue': round(revenue, 2),
            'target': round(target, 2),
            'salary': round(salary, 2),
            'achievement': round(achievement, 1),
            'salary_percent': round(salary_percent, 1),
        })

    # Previous month data (for MoM growth and AI insights)
    previous_month_metrics = {}
    previous_revenue = None
    if included_months:
        first_month_index = CALENDAR_MONTHS.index(included_months[0])
        if first_month_index > 0:
            prev_month, prev_year = CALENDAR_MONTHS[first_month_index - 1], year
        else:
            prev_month, prev_year = 'December', year - 1

        prev_row = cur.execute(
            'SELECT COALESCE(SUM(revenue), 0) AS total_revenue FROM monthly_data WHERE year = ? AND month = ?',
            (prev_year, prev_month),
        ).fetchone()
        if prev_row and prev_row['total_revenue'] > 0:
            previous_revenue = float(prev_row['total_revenue'])

        prev_center_rows = cur.execute(
            """
            SELECT center_id,
                   COALESCE(SUM(revenue), 0) AS total_revenue,
                   COALESCE(SUM(target), 0) AS total_target
            FROM monthly_data
            WHERE year = ? AND month = ?
            GROUP BY center_id
            """,
            (prev_year, prev_month),
        ).fetchall()
        previous_month_metrics = {
            row['center_id']: {
                'revenue': float(row['total_revenue'] or 0),
                'target': float(row['total_target'] or 0),
            }
            for row in prev_center_rows
        }

    conn.close()

    total_revenue = round(sum(c['revenue'] for c in centers), 2)
    total_target = round(sum(c['target'] for c in centers), 2)
    total_salary = round(sum(c['salary'] for c in centers), 2)
    achievement_pct = round((total_revenue / total_target * 100) if total_target > 0 else 0, 1)
    remaining_revenue = round(max(total_target - total_revenue, 0), 2)
    achieved_revenue = round(total_revenue, 2)
    avg_salary_pct = round((total_salary / total_revenue * 100) if total_revenue > 0 else 0, 1)
    ranked_centers = sorted(centers, key=lambda x: x['achievement'], reverse=True)
    best_center = ranked_centers[0]['name'] if ranked_centers else 'N/A'

    # Monthly trend + MoM growth
    monthly_trend = []
    monthly_growth = []
    prev_rev = previous_revenue
    for month in included_months:
        mr = round(monthly_totals.get(month, {}).get('revenue', 0), 2)
        mt_val = round(monthly_totals.get(month, {}).get('target', 0), 2)
        m_ach = round((mr / mt_val * 100) if mt_val > 0 else 0, 1)
        growth = None if (prev_rev is None or prev_rev == 0) else round(((mr - prev_rev) / prev_rev) * 100, 1)
        monthly_trend.append({'month': month, 'revenue': mr, 'target': mt_val, 'achievement': m_ach, 'growth': growth})
        monthly_growth.append(growth)
        prev_rev = mr

    # Smart alerts
    alerts = []
    for c in ranked_centers:
        reasons = []
        if c['achievement'] < 80:
            reasons.append(f"Achievement only {c['achievement']}%")
        if c['salary_percent'] > 30:
            reasons.append(f"Salary % high at {c['salary_percent']}%")
        if reasons:
            alerts.append({
                'center': c['name'],
                'severity': 'high' if c['achievement'] < 60 else 'medium',
                'message': ' | '.join(reasons),
            })

    # AI insights
    ai_insights = _build_ai_insights(
        year=year,
        included_months=included_months,
        centers=centers,
        ranked_centers=ranked_centers,
        monthly_growth=monthly_growth,
        center_month_history=center_month_history,
        previous_month_metrics=previous_month_metrics,
    )

    return {
        'total_target': total_target,
        'achieved_revenue': achieved_revenue,
        'remaining_revenue': remaining_revenue,
        'achievement_pct': achievement_pct,
        'best_center': best_center,
        'avg_salary_pct': avg_salary_pct,
        'centers': ranked_centers,
        'monthly_trend': monthly_trend,
        'alerts': alerts,
        'ai_insights': ai_insights.get('items', []),
    }


def _build_email_summary_snapshot_filtered(start_month, start_year, end_month, end_year, selected_center=None):
    start_month, start_year, end_month, end_year, included_periods = _sanitize_month_year_range(
        start_month,
        start_year,
        end_month,
        end_year,
    )
    period_labels = [f'{month} {year}' for month, year in included_periods]
    included_period_set = set(included_periods)
    center_query = _normalize_center_name(selected_center)

    conn = get_db()
    cur = conn.cursor()

    center_lookup_rows = cur.execute(
        'SELECT id, name FROM centers ORDER BY name COLLATE NOCASE'
    ).fetchall()

    if center_query:
        exact_matches = [row for row in center_lookup_rows if _normalize_center_name(row['name']) == center_query]
        matched_rows = exact_matches or [row for row in center_lookup_rows if center_query in _normalize_center_name(row['name'])]
        selected_center_ids = {row['id'] for row in matched_rows}
        selected_center_names = [row['name'] for row in matched_rows]
        scope_center_label = selected_center_names[0] if len(selected_center_names) == 1 else (selected_center or '').strip()
    else:
        selected_center_ids = None
        selected_center_names = []
        scope_center_label = 'All Centers'

    monthly_center_rows = cur.execute(
        """
        SELECT center_id,
               month,
               year,
               COALESCE(SUM(revenue), 0) AS total_revenue,
               COALESCE(SUM(target), 0) AS total_target
        FROM monthly_data
        GROUP BY center_id, month, year
        """
    ).fetchall()

    monthly_center_totals = {
        (row['center_id'], f"{row['month']} {int(row['year'])}"): {
            'revenue': float(row['total_revenue'] or 0),
            'target': float(row['total_target'] or 0),
        }
        for row in monthly_center_rows
        if (row['month'], int(row['year'])) in included_period_set
        and (selected_center_ids is None or row['center_id'] in selected_center_ids)
    }

    salary_rows = cur.execute(
        """
        SELECT co.center_id,
               cs.coach_id,
               cs.month,
               cs.year,
               COALESCE(cs.salary, 0) AS salary
        FROM coach_salaries cs
        JOIN coaches co ON cs.coach_id = co.id
        WHERE co.end_month IS NULL
          AND co.end_year IS NULL
        """
    ).fetchall()

    salary_by_center_month = {}
    salary_by_center = {}
    for row in salary_rows:
        cid = row['center_id']
        if selected_center_ids is not None and cid not in selected_center_ids:
            continue

        month_name = row['month']
        month_year = int(row['year'])
        if (month_name, month_year) not in included_period_set:
            continue

        period_label = f'{month_name} {month_year}'
        salary_info = calculate_final_salary_for_month(
            cur,
            coach_id=row['coach_id'],
            year=month_year,
            month_name=month_name,
            monthly_salary=float(row['salary'] or 0),
        )
        final_salary = float(salary_info['final_salary'] or 0)
        salary_by_center_month[(cid, period_label)] = salary_by_center_month.get((cid, period_label), 0.0) + final_salary
        salary_by_center[cid] = salary_by_center.get(cid, 0.0) + final_salary

    centers = []
    center_month_history = {}
    for row in center_lookup_rows:
        cid = row['id']
        if selected_center_ids is not None and cid not in selected_center_ids:
            continue

        revenue = 0.0
        target = 0.0
        center_month_history[cid] = {}
        for period_label in period_labels:
            pt = monthly_center_totals.get((cid, period_label), {'revenue': 0.0, 'target': 0.0})
            mr = float(pt['revenue'] or 0)
            mt = float(pt['target'] or 0)
            ms = float(salary_by_center_month.get((cid, period_label), 0.0))

            revenue += mr
            target += mt
            center_month_history[cid][period_label] = {
                'revenue': round(mr, 2),
                'target': round(mt, 2),
                'salary': round(ms, 2),
                'achievement': round((mr / mt * 100) if mt > 0 else 0, 1),
                'salary_percent': round((ms / mr * 100) if mr > 0 else 0, 1),
            }

        salary = float(salary_by_center.get(cid, 0.0))
        achievement = (revenue / target * 100) if target > 0 else 0
        salary_percent = (salary / revenue * 100) if revenue > 0 else 0
        centers.append({
            'id': cid,
            'name': row['name'],
            'revenue': round(revenue, 2),
            'target': round(target, 2),
            'salary': round(salary, 2),
            'achievement': round(achievement, 1),
            'salary_percent': round(salary_percent, 1),
        })

    monthly_totals = {}
    for (_, period_label), values in monthly_center_totals.items():
        totals = monthly_totals.setdefault(period_label, {'revenue': 0.0, 'target': 0.0})
        totals['revenue'] += float(values['revenue'] or 0)
        totals['target'] += float(values['target'] or 0)

    previous_month_metrics = {}
    previous_revenue = None
    if included_periods:
        first_month, first_year = included_periods[0]
        prev_month, prev_year = _previous_month_period(first_month, first_year)
        prev_rows = cur.execute(
            """
            SELECT center_id,
                   COALESCE(SUM(revenue), 0) AS total_revenue,
                   COALESCE(SUM(target), 0) AS total_target
            FROM monthly_data
            WHERE year = ? AND month = ?
            GROUP BY center_id
            """,
            (prev_year, prev_month),
        ).fetchall()
        prev_total = 0.0
        for row in prev_rows:
            cid = row['center_id']
            if selected_center_ids is not None and cid not in selected_center_ids:
                continue
            rev = float(row['total_revenue'] or 0)
            tgt = float(row['total_target'] or 0)
            previous_month_metrics[cid] = {'revenue': rev, 'target': tgt}
            prev_total += rev
        if prev_total > 0:
            previous_revenue = prev_total

    conn.close()

    total_revenue = round(sum(c['revenue'] for c in centers), 2)
    total_target = round(sum(c['target'] for c in centers), 2)
    total_salary = round(sum(c['salary'] for c in centers), 2)
    achievement_pct = round((total_revenue / total_target * 100) if total_target > 0 else 0, 1)
    remaining_revenue = round(max(total_target - total_revenue, 0), 2)
    ranked_centers = sorted(centers, key=lambda x: x['achievement'], reverse=True)
    best_center = ranked_centers[0]['name'] if ranked_centers else 'N/A'

    monthly_trend = []
    monthly_growth = []
    prev_rev = previous_revenue
    for period_label in period_labels:
        mr = round(monthly_totals.get(period_label, {}).get('revenue', 0), 2)
        mt = round(monthly_totals.get(period_label, {}).get('target', 0), 2)
        growth = None if (prev_rev is None or prev_rev == 0) else round(((mr - prev_rev) / prev_rev) * 100, 1)
        monthly_trend.append({
            'month': period_label,
            'revenue': mr,
            'target': mt,
            'achievement': round((mr / mt * 100) if mt > 0 else 0, 1),
            'growth': growth,
        })
        monthly_growth.append(growth)
        prev_rev = mr

    alerts = []
    for center in ranked_centers:
        reasons = []
        if center['achievement'] < 80:
            reasons.append(f"Achievement only {center['achievement']}%")
        if center['salary_percent'] > 30:
            reasons.append(f"Salary % high at {center['salary_percent']}%")
        if reasons:
            alerts.append({
                'center': center['name'],
                'severity': 'high' if center['achievement'] < 60 else 'medium',
                'message': ' | '.join(reasons),
            })

    ai_insights = _build_ai_insights(
        year=end_year,
        included_months=period_labels,
        centers=centers,
        ranked_centers=ranked_centers,
        monthly_growth=monthly_growth,
        center_month_history=center_month_history,
        previous_month_metrics=previous_month_metrics,
    )

    return {
        'total_target': total_target,
        'achieved_revenue': total_revenue,
        'remaining_revenue': remaining_revenue,
        'achievement_pct': achievement_pct,
        'best_center': best_center,
        'avg_salary_pct': round((total_salary / total_revenue * 100) if total_revenue > 0 else 0, 1),
        'centers': ranked_centers,
        'monthly_trend': monthly_trend,
        'alerts': alerts,
        'ai_insights': ai_insights.get('items', []),
        'start_month': start_month,
        'start_year': start_year,
        'end_month': end_month,
        'end_year': end_year,
        'scope_center_label': scope_center_label,
        'scope_selected_center': (selected_center or '').strip(),
        'scope_center_match_count': len(selected_center_names),
        'scope_is_filtered': bool(center_query),
    }


def send_email_report(summary, year, from_month, to_month, recipients):
        """Send analytics summary report to one or more recipients via Gmail SMTP."""
        smtp_user = (os.environ.get('GMAIL_SMTP_USER') or '').strip()
        smtp_password = (os.environ.get('GMAIL_SMTP_PASSWORD') or '').strip()
        smtp_host = (os.environ.get('GMAIL_SMTP_HOST') or 'smtp.gmail.com').strip()
        smtp_port = int(os.environ.get('GMAIL_SMTP_PORT') or 587)
        sender_name = (os.environ.get('GMAIL_SENDER_NAME') or 'Academy Dashboard').strip()
        from_address = (os.environ.get('GMAIL_SMTP_FROM') or smtp_user).strip()

        if not smtp_user or not smtp_password:
                return {
                        'ok': False,
                        'error': 'Missing Gmail SMTP credentials. Set GMAIL_SMTP_USER and GMAIL_SMTP_PASSWORD.',
                }

        if not from_address:
                return {
                        'ok': False,
                        'error': 'Missing sender email. Set GMAIL_SMTP_FROM or GMAIL_SMTP_USER.',
                }

        from_month = summary.get('start_month', datetime.now().strftime('%B'))
        from_year = summary.get('start_year', datetime.now().year)
        to_month = summary.get('end_month', datetime.now().strftime('%B'))
        to_year = summary.get('end_year', datetime.now().year)
        scope_center_label = summary.get('scope_center_label') or 'All Centers'
        scope_is_filtered = bool(summary.get('scope_is_filtered'))
        scope_center_match_count = int(summary.get('scope_center_match_count') or 0)
        is_single_center_scope = scope_is_filtered and scope_center_match_count == 1
        period_scope_text = f'{from_month[:3]} {from_year} - {to_month[:3]} {to_year}'
        scope_text = f'{scope_center_label} ({period_scope_text})'
        subject = f'Analytics Report - {scope_text}'
        generated_at = datetime.now().strftime('%d %b %Y %I:%M %p')

        # --- KPI summary cards ---
        kpi_items = [
                ('Total Target', _format_currency(summary['total_target'])),
                ('Achieved Revenue', _format_currency(summary['achieved_revenue'])),
                ('Remaining Target', _format_currency(summary['remaining_revenue'])),
                ('Achievement %', f"{summary['achievement_pct']}%"),
            ('Center', escape(scope_center_label)) if is_single_center_scope else ('Best Center', escape(summary['best_center'])),
                ('Average Salary %', f"{summary['avg_salary_pct']}%"),
        ]

        def _kpi_cell(label, value):
                return (
                        '<td style="width:33.33%;padding:5px;vertical-align:top;">'
                        '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 12px;">'
                        f'<div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;">{label}</div>'
                        f'<div style="font-size:16px;font-weight:700;color:#0f172a;margin-top:4px;">{value}</div>'
                        '</div></td>'
                )

        kpi_row1 = ''.join(_kpi_cell(l, v) for l, v in kpi_items[:3])
        kpi_row2 = ''.join(_kpi_cell(l, v) for l, v in kpi_items[3:])
        kpi_section = (
                '<tr><td style="padding:16px 16px 0;">'
                '<div style="font-size:13px;font-weight:700;color:#1e3a8a;border-bottom:2px solid #e2e8f0;'
                'padding-bottom:6px;margin-bottom:10px;">Portfolio Summary</div>'
                '<table role="presentation" width="100%" cellspacing="0" cellpadding="0">'
                f'<tr>{kpi_row1}</tr><tr>{kpi_row2}</tr>'
                '</table></td></tr>'
        )

        # --- Monthly trend table ---
        monthly_trend = summary.get('monthly_trend', [])
        if monthly_trend:
                trend_rows = ''
                for i, mt in enumerate(monthly_trend):
                        bg = '#f8fafc' if i % 2 == 0 else '#ffffff'
                        growth_str = (f"{mt['growth']:+.1f}%" if mt['growth'] is not None else '&mdash;')
                        growth_color = '#15803d' if (mt['growth'] or 0) >= 0 else '#dc2626'
                        ach_color = '#15803d' if mt['achievement'] >= 100 else ('#d97706' if mt['achievement'] >= 80 else '#dc2626')
                        trend_rows += (
                                f'<tr style="background:{bg};">'
                                f'<td style="padding:7px 10px;font-weight:600;font-size:13px;">{escape(mt["month"][:3])}</td>'
                                f'<td style="padding:7px 10px;text-align:right;font-size:13px;">{_format_currency(mt["revenue"])}</td>'
                                f'<td style="padding:7px 10px;color:#475569;text-align:right;font-size:13px;">{_format_currency(mt["target"])}</td>'
                                f'<td style="padding:7px 10px;font-weight:700;color:{ach_color};text-align:right;font-size:13px;">{mt["achievement"]}%</td>'
                                f'<td style="padding:7px 10px;font-weight:600;color:{growth_color};text-align:right;font-size:13px;">{growth_str}</td>'
                                '</tr>'
                        )
                trend_section = (
                        '<tr><td style="padding:16px 16px 0;">'
                        '<div style="font-size:13px;font-weight:700;color:#1e3a8a;border-bottom:2px solid #e2e8f0;'
                        'padding-bottom:6px;margin-bottom:10px;">Monthly Revenue Trend</div>'
                        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
                        'style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">'
                        '<thead><tr style="background:#0f172a;color:#f8fafc;">'
                        '<th style="padding:7px 10px;text-align:left;font-size:11px;">Month</th>'
                        '<th style="padding:7px 10px;text-align:right;font-size:11px;">Revenue</th>'
                        '<th style="padding:7px 10px;text-align:right;font-size:11px;">Target</th>'
                        '<th style="padding:7px 10px;text-align:right;font-size:11px;">Achievement</th>'
                        '<th style="padding:7px 10px;text-align:right;font-size:11px;">MoM Growth</th>'
                        f'</tr></thead><tbody>{trend_rows}</tbody></table></td></tr>'
                )
        else:
                trend_section = ''

        # --- Center performance table ---
        centers = summary.get('centers', [])
        if centers:
                center_rows_html = ''
                for i, c in enumerate(centers):
                        bg = '#f8fafc' if i % 2 == 0 else '#ffffff'
                        ach_color = '#15803d' if c['achievement'] >= 100 else ('#d97706' if c['achievement'] >= 80 else '#dc2626')
                        sal_color = '#dc2626' if c['salary_percent'] > 30 else '#15803d'
                        center_rows_html += (
                                f'<tr style="background:{bg};">'
                                f'<td style="padding:7px 10px;font-weight:600;font-size:13px;">{escape(c["name"])}</td>'
                                f'<td style="padding:7px 10px;text-align:right;font-size:13px;">{_format_currency(c["revenue"])}</td>'
                                f'<td style="padding:7px 10px;color:#475569;text-align:right;font-size:13px;">{_format_currency(c["target"])}</td>'
                                f'<td style="padding:7px 10px;font-weight:700;color:{ach_color};text-align:right;font-size:13px;">{c["achievement"]}%</td>'
                                f'<td style="padding:7px 10px;font-weight:600;color:{sal_color};text-align:right;font-size:13px;">{c["salary_percent"]}%</td>'
                                '</tr>'
                        )
                centers_section = (
                        '<tr><td style="padding:16px 16px 0;">'
                        '<div style="font-size:13px;font-weight:700;color:#1e3a8a;border-bottom:2px solid #e2e8f0;'
                        'padding-bottom:6px;margin-bottom:10px;">Center Performance (ranked by Achievement)</div>'
                        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
                        'style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">'
                        '<thead><tr style="background:#0f172a;color:#f8fafc;">'
                        '<th style="padding:7px 10px;text-align:left;font-size:11px;">Center</th>'
                        '<th style="padding:7px 10px;text-align:right;font-size:11px;">Revenue</th>'
                        '<th style="padding:7px 10px;text-align:right;font-size:11px;">Target</th>'
                        '<th style="padding:7px 10px;text-align:right;font-size:11px;">Achievement</th>'
                        '<th style="padding:7px 10px;text-align:right;font-size:11px;">Salary %</th>'
                        f'</tr></thead><tbody>{center_rows_html}</tbody></table></td></tr>'
                )
        else:
                centers_section = ''

        # --- Smart alerts ---
        alerts = summary.get('alerts', [])
        if alerts:
                alert_rows = ''
                for alert in alerts:
                        bc = '#dc2626' if alert['severity'] == 'high' else '#f59e0b'
                        bg = '#fef2f2' if alert['severity'] == 'high' else '#fffbeb'
                        alert_rows += (
                                f'<tr><td style="padding:4px 0;">'
                                f'<div style="border-left:4px solid {bc};background:{bg};border-radius:6px;padding:8px 12px;">'
                                f'<span style="font-weight:700;color:#0f172a;font-size:13px;">{escape(alert["center"])}</span> '
                                f'<span style="color:#374151;font-size:13px;">&mdash; {escape(alert["message"])}</span>'
                                f'</div></td></tr>'
                        )
                alerts_section = (
                        '<tr><td style="padding:16px 16px 0;">'
                        '<div style="font-size:13px;font-weight:700;color:#1e3a8a;border-bottom:2px solid #e2e8f0;'
                        'padding-bottom:6px;margin-bottom:10px;">Smart Alerts</div>'
                        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0">'
                        f'{alert_rows}</table></td></tr>'
                )
        else:
                alerts_section = (
                        '<tr><td style="padding:16px 16px 0;">'
                        '<div style="font-size:13px;font-weight:700;color:#1e3a8a;border-bottom:2px solid #e2e8f0;'
                        'padding-bottom:6px;margin-bottom:10px;">Smart Alerts</div>'
                        '<div style="background:#f0fdf4;border-left:4px solid #22c55e;border-radius:6px;'
                        'padding:10px 12px;color:#15803d;font-size:13px;">'
                        'All centers are performing within thresholds.</div>'
                        '</td></tr>'
                )

        # --- AI insights ---
        ai_items = summary.get('ai_insights', [])
        if ai_items:
                sev_border = {'high': '#dc2626', 'medium': '#f59e0b', 'info': '#22c55e'}
                sev_bg = {'high': '#fef2f2', 'medium': '#fffbeb', 'info': '#f0fdf4'}
                ai_rows = ''
                for item in ai_items:
                        sev = item.get('severity', 'info')
                        bc = sev_border.get(sev, '#22c55e')
                        bg = sev_bg.get(sev, '#f0fdf4')
                        category = escape(item.get('category', '').replace('_', ' ').title())
                        action_html = (
                                f'<div style="margin-top:4px;font-size:12px;color:#475569;">'
                                f'Action: {escape(item.get("action", ""))}</div>'
                                if item.get('action') else ''
                        )
                        ai_rows += (
                                f'<tr><td style="padding:4px 0;">'
                                f'<div style="border-left:4px solid {bc};background:{bg};border-radius:6px;padding:8px 12px;">'
                                f'<div style="font-size:11px;color:#64748b;font-weight:700;">#{item.get("rank","")} {category}'
                                f' &nbsp;&bull;&nbsp; <span style="color:{bc};">{sev.upper()}</span></div>'
                                f'<p style="margin:4px 0 0;color:#0f172a;font-size:13px;line-height:1.5;">'
                                f'{escape(item.get("message", ""))}</p>'
                                f'{action_html}</div></td></tr>'
                        )
                ai_section = (
                        '<tr><td style="padding:16px 16px 0;">'
                        '<div style="font-size:13px;font-weight:700;color:#1e3a8a;border-bottom:2px solid #e2e8f0;'
                        'padding-bottom:6px;margin-bottom:10px;">AI Insights</div>'
                        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0">'
                        f'{ai_rows}</table></td></tr>'
                )
        else:
                ai_section = ''

        html_body = (
                '<html><body style="margin:0;background:#e2e8f0;font-family:Arial,sans-serif;color:#0f172a;">'
                '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="padding:24px 12px;">'
                '<tr><td align="center">'
                '<table role="presentation" width="680" cellspacing="0" cellpadding="0" '
                'style="max-width:680px;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #cbd5e1;">'
                '<tr><td style="padding:20px 24px;background:linear-gradient(135deg,#0f172a,#1e3a8a);color:#f8fafc;">'
                '<div style="font-size:20px;font-weight:700;">Executive Analytics Report</div>'
                f'<div style="font-size:13px;opacity:0.9;margin-top:6px;">{escape(period_scope_text)}</div>'
                f'<div style="font-size:13px;opacity:0.9;margin-top:4px;">Report Scope: {escape(scope_center_label)} ({escape(period_scope_text)})</div>'
                '</td></tr>'
                + kpi_section
                + trend_section
                + centers_section
                + alerts_section
                + ai_section
                + '<tr><td style="padding:14px 24px 20px;color:#64748b;font-size:12px;border-top:1px solid #e2e8f0;">'
                f'Generated on {generated_at} by Academy Dashboard.'
                '</td></tr>'
                '</table></td></tr></table></body></html>'
        )

        # Plain-text fallback
        text_lines = [
            f'Executive Analytics Report ({period_scope_text})',
                f'Report Scope: {scope_center_label} ({period_scope_text})',
                f'Generated: {generated_at}',
                '',
                'PORTFOLIO SUMMARY',
                f"Total Target: {_format_currency(summary['total_target'])}",
                f"Achieved Revenue: {_format_currency(summary['achieved_revenue'])}",
                f"Remaining Target: {_format_currency(summary['remaining_revenue'])}",
                f"Achievement %: {summary['achievement_pct']}%",
                f"Center: {scope_center_label}" if is_single_center_scope else f"Best Center: {summary['best_center']}",
                f"Average Salary %: {summary['avg_salary_pct']}%",
        ]
        if monthly_trend:
                text_lines += ['', 'MONTHLY TREND']
                for mt in monthly_trend:
                        g = f"{mt['growth']:+.1f}%" if mt['growth'] is not None else '-'
                        text_lines.append(
                                f"{mt['month'][:3]}: Revenue {_format_currency(mt['revenue'])} | "
                                f"Target {_format_currency(mt['target'])} | Achievement {mt['achievement']}% | Growth {g}"
                        )
        if centers:
                text_lines += ['', 'CENTER PERFORMANCE']
                for c in centers:
                        text_lines.append(
                                f"{c['name']}: Revenue {_format_currency(c['revenue'])} | "
                                f"Target {_format_currency(c['target'])} | Achievement {c['achievement']}% | Salary% {c['salary_percent']}%"
                        )
        if alerts:
                text_lines += ['', 'SMART ALERTS']
                for a in alerts:
                        text_lines.append(f"[{a['severity'].upper()}] {a['center']}: {a['message']}")
        if ai_items:
                text_lines += ['', 'AI INSIGHTS']
                for item in ai_items:
                        text_lines.append(f"#{item.get('rank','')} [{item.get('severity','').upper()}] {item.get('message','')}")
                        if item.get('action'):
                                text_lines.append(f"  Action: {item['action']}")
        text_body = '\n'.join(text_lines)

        report_jpg = _build_report_jpg(
            f'{from_year}-{to_year}',
            from_month,
            to_month,
            summary,
            monthly_trend,
            centers,
            alerts,
            ai_items,
        )

        message = MIMEMultipart('mixed')
        message['Subject'] = subject
        message['From'] = f'{sender_name} <{from_address}>'
        message['To'] = ', '.join(recipients)

        alternative_part = MIMEMultipart('alternative')
        alternative_part.attach(MIMEText(text_body, 'plain'))
        alternative_part.attach(MIMEText(html_body, 'html'))
        message.attach(alternative_part)

        if report_jpg:
            file_name = f'analytics_report_{from_year}_{from_month}_{to_year}_{to_month}.jpg'.replace(' ', '_')
            image_part = MIMEImage(report_jpg, _subtype='jpeg', name=file_name)
            image_part.add_header('Content-Disposition', 'attachment', filename=file_name)
            message.attach(image_part)

        try:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as smtp:
                        smtp.starttls()
                        smtp.login(smtp_user, smtp_password)
                        smtp.sendmail(from_address, recipients, message.as_string())
        except Exception as exc:
                return {
                        'ok': False,
                        'error': f'Failed to send email: {exc}',
                }

        return {
                'ok': True,
                'message': f'Report sent to {len(recipients)} recipient(s).',
        }


def _fetch_summer_camp_dashboard_totals(cur, year, base_target_months):
    months = _sanitize_base_target_months(base_target_months)
    month_placeholders = ','.join('?' * len(months))
    dashboard_rows = cur.execute(
        """
        SELECT c.name,
               COALESCE(SUM(md.target), 0) AS target,
               COALESCE(SUM(md.revenue), 0) AS revenue
        FROM centers c
        LEFT JOIN monthly_data md
          ON md.center_id = c.id
         AND md.year = ?
         AND md.month IN ({})
        GROUP BY c.id, c.name
        """.format(month_placeholders),
        (year, *months),
    ).fetchall()

    targets_by_name = {}
    revenues_by_name = {}
    for row in dashboard_rows:
        key = _normalize_center_name(row['name'])
        target = float(row['target'] or 0)
        revenue = float(row['revenue'] or 0)
        if target > 0:
            targets_by_name[key] = target
        if revenue > 0:
            revenues_by_name[key] = revenue

    return targets_by_name, revenues_by_name


def _ensure_summer_camp_center_config(cur):
    """Ensure center config table exists and includes all centers."""
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS summer_camp_centers_config(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            center_id INTEGER NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(center_id) REFERENCES centers(id)
        )
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_summer_camp_centers_config_center
        ON summer_camp_centers_config(center_id)
        """
    )

    # Auto-register newly created centers as active in Summer Camp view.
    cur.execute(
        """
        INSERT INTO summer_camp_centers_config(center_id, is_active, updated_at)
        SELECT c.id, 1, CURRENT_TIMESTAMP
        FROM centers c
        LEFT JOIN summer_camp_centers_config cfg ON cfg.center_id = c.id
        WHERE cfg.center_id IS NULL
        """
    )


def _fetch_summer_camp_center_catalog(cur):
    _ensure_summer_camp_center_config(cur)
    center_rows = cur.execute(
        """
        SELECT c.id AS center_id,
               TRIM(c.name) AS center,
               COALESCE(cfg.is_active, 1) AS is_active
        FROM centers c
        LEFT JOIN summer_camp_centers_config cfg ON cfg.center_id = c.id
        WHERE TRIM(COALESCE(c.name, '')) <> ''
        ORDER BY TRIM(c.name) COLLATE NOCASE
        """
    ).fetchall()
    return [
        {
            'center_id': row['center_id'],
            'center': row['center'],
            'is_active': bool(row['is_active']),
        }
        for row in center_rows
    ]


def _fetch_active_summer_camp_centers(cur):
    return [
        row
        for row in _fetch_summer_camp_center_catalog(cur)
        if row['is_active']
    ]


def _build_summer_camp_payload(cur, month, year, base_target_months=None):
    selected_base_target_months = _sanitize_base_target_months(base_target_months)
    targets_by_name, dashboard_revenue_by_name = _fetch_summer_camp_dashboard_totals(
        cur,
        year,
        selected_base_target_months,
    )
    active_centers = _fetch_active_summer_camp_centers(cur)
    revenue_rows = cur.execute(
        """
        SELECT center_name, COALESCE(revenue, 0) AS revenue
        FROM summer_camp_incentives
        WHERE month = ? AND year = ?
        """,
        (month, year),
    ).fetchall()

    revenue_by_name = {
        _normalize_center_name(row['center_name']): float(row['revenue'] or 0)
        for row in revenue_rows
    }

    rows = []
    total_summer_revenue = 0.0
    total_incentive = 0.0
    total_achievement = 0.0

    for center in active_centers:
        center_name = center['center']
        normalized_name = _normalize_center_name(center_name)
        fallback_target = SUMMER_CAMP_BASE_TARGETS.get(center_name, 0.0)
        base_target = round(
            targets_by_name.get(normalized_name, fallback_target),
            2,
        )
        dashboard_revenue = round(dashboard_revenue_by_name.get(normalized_name, 0.0), 2)
        summer_revenue = round(revenue_by_name.get(normalized_name, 0.0), 2)
        total_revenue = round(dashboard_revenue + summer_revenue, 2)
        excess_amount = round(max(0.0, total_revenue - base_target), 2)
        threshold_target = round(base_target * 0.80, 2)
        incentive_amount = round(excess_amount * 0.10, 2)
        achievement_pct = round((total_revenue / base_target * 100) if base_target > 0 else 0.0, 1)

        if achievement_pct >= 100:
            status = 'green'
            status_label = 'Above 100%'
        elif achievement_pct >= 80:
            status = 'yellow'
            status_label = '80-99% range'
        else:
            status = 'red'
            status_label = 'Below 80%'

        rows.append(
            {
                'center_id': center['center_id'],
                'center': center_name,
                'base_target': base_target,
                'threshold_target': threshold_target,
                'dashboard_revenue': dashboard_revenue,
                'summer_revenue': summer_revenue,
                'total_revenue': total_revenue,
                'excess_amount': excess_amount,
                'incentive_amount': incentive_amount,
                'achievement_pct': achievement_pct,
                'status': status,
                'status_label': status_label,
                'progress_width': min(achievement_pct, 100),
            }
        )

        total_summer_revenue += summer_revenue
        total_incentive += incentive_amount
        total_achievement += achievement_pct

    summary = {
        'total_summer_revenue': round(total_summer_revenue, 2),
        'total_incentive_pool': round(total_incentive, 2),
        'average_target_achievement': round((total_achievement / len(rows)) if rows else 0.0, 1),
    }

    return rows, summary, selected_base_target_months


def _month_sort_key(month_name):
    try:
        return CALENDAR_MONTHS.index(month_name)
    except ValueError:
        return len(CALENDAR_MONTHS)


def _previous_month_period(month_name, year):
    month_index = CALENDAR_MONTHS.index(month_name)
    if month_index == 0:
        return CALENDAR_MONTHS[-1], year - 1
    return CALENDAR_MONTHS[month_index - 1], year


def _format_currency(amount):
    value = round(float(amount or 0), 2)
    if value.is_integer():
        return f'₹{value:,.0f}'
    return f'₹{value:,.2f}'


def _build_insight(
    category,
    severity,
    priority,
    message,
    center=None,
    needs_action=False,
    action=None,
    metrics=None,
):
    center_key = _normalize_center_name(center).replace(' ', '-') if center else 'portfolio'
    return {
        'id': f'{category}-{center_key}',
        'category': category,
        'severity': severity,
        'priority': round(float(priority), 1),
        'message': message,
        'center': center,
        'needs_action': needs_action,
        'action': action,
        'metrics': metrics or {},
    }


def _select_top_insights(candidates, limit=5):
    severity_rank = {'high': 3, 'medium': 2, 'info': 1}
    ordered = sorted(
        candidates,
        key=lambda item: (
            item['needs_action'],
            severity_rank.get(item['severity'], 0),
            item['priority'],
        ),
        reverse=True,
    )

    selected = []
    seen_ids = set()
    for candidate in ordered:
        if candidate['id'] in seen_ids:
            continue
        selected.append(candidate)
        seen_ids.add(candidate['id'])
        if len(selected) == limit:
            break

    for index, item in enumerate(selected, start=1):
        item['rank'] = index

    return selected


def _build_ai_insights(
    year,
    included_months,
    centers,
    ranked_centers,
    monthly_growth,
    center_month_history,
    previous_month_metrics,
):
    latest_month = included_months[-1] if included_months else None
    candidates = []

    if latest_month:
        for center in centers:
            center_id = center['id']
            center_name = center['name']
            latest_metrics = center_month_history.get(center_id, {}).get(
                latest_month,
                {'revenue': 0.0, 'target': 0.0, 'salary': 0.0, 'achievement': 0.0, 'salary_percent': 0.0},
            )

            target_gap = max(0.0, latest_metrics['target'] - latest_metrics['revenue'])
            if latest_metrics['target'] > 0 and target_gap > 0:
                candidates.append(
                    _build_insight(
                        category='target_achievement',
                        severity='high' if latest_metrics['achievement'] < 80 else 'medium',
                        priority=160 - latest_metrics['achievement'],
                        message=f"{center_name} needs {_format_currency(target_gap)} more to hit target in {latest_month}.",
                        center=center_name,
                        needs_action=True,
                        action=(
                            f"Close a {_format_currency(target_gap)} shortfall against the "
                            f"{_format_currency(latest_metrics['target'])} target."
                        ),
                        metrics={
                            'month': latest_month,
                            'year': year,
                            'revenue': latest_metrics['revenue'],
                            'target': latest_metrics['target'],
                            'gap': round(target_gap, 2),
                            'achievement_pct': latest_metrics['achievement'],
                        },
                    )
                )

            if latest_metrics['revenue'] > 0 and latest_metrics['salary_percent'] > 30:
                candidates.append(
                    _build_insight(
                        category='salary_percent',
                        severity='high' if latest_metrics['salary_percent'] >= 40 else 'medium',
                        priority=140 + (latest_metrics['salary_percent'] - 30),
                        message=(
                            f"{center_name} salary percentage is {latest_metrics['salary_percent']}%, "
                            "above the recommended 30%."
                        ),
                        center=center_name,
                        needs_action=True,
                        action='Review coach allocation or improve revenue conversion this month.',
                        metrics={
                            'month': latest_month,
                            'year': year,
                            'salary_percent': latest_metrics['salary_percent'],
                            'recommended_percent': 30.0,
                            'salary': latest_metrics['salary'],
                            'revenue': latest_metrics['revenue'],
                        },
                    )
                )

            previous_metrics = previous_month_metrics.get(center_id)
            if previous_metrics and previous_metrics.get('revenue', 0) > 0:
                growth_pct = round(
                    ((latest_metrics['revenue'] - previous_metrics['revenue']) / previous_metrics['revenue']) * 100,
                    1,
                )
                if growth_pct <= -10:
                    candidates.append(
                        _build_insight(
                            category='month_over_month_growth',
                            severity='high' if growth_pct <= -20 else 'medium',
                            priority=135 + abs(growth_pct),
                            message=f"{center_name} revenue dropped {abs(growth_pct)}% compared to last month.",
                            center=center_name,
                            needs_action=True,
                            action='Investigate lead flow, retention, and recent deal slippage.',
                            metrics={
                                'month': latest_month,
                                'year': year,
                                'growth_pct': growth_pct,
                                'current_revenue': latest_metrics['revenue'],
                                'previous_revenue': previous_metrics['revenue'],
                            },
                        )
                    )
                elif growth_pct >= 15:
                    candidates.append(
                        _build_insight(
                            category='month_over_month_growth',
                            severity='info',
                            priority=70 + growth_pct,
                            message=f"{center_name} revenue grew {growth_pct}% compared to last month.",
                            center=center_name,
                            needs_action=False,
                            action='Capture the channel or offer that drove this lift and replicate it.',
                            metrics={
                                'month': latest_month,
                                'year': year,
                                'growth_pct': growth_pct,
                                'current_revenue': latest_metrics['revenue'],
                                'previous_revenue': previous_metrics['revenue'],
                            },
                        )
                    )

            streak = 0
            best_streak = 0
            for month_name in sorted(included_months, key=_month_sort_key):
                metrics = center_month_history.get(center_id, {}).get(month_name)
                if metrics and metrics['target'] > 0 and metrics['achievement'] >= 100:
                    streak += 1
                    best_streak = max(best_streak, streak)
                else:
                    streak = 0

            if best_streak >= 3:
                candidates.append(
                    _build_insight(
                        category='revenue',
                        severity='info',
                        priority=85 + best_streak,
                        message=f"{center_name} exceeded target for {best_streak} consecutive months.",
                        center=center_name,
                        needs_action=False,
                        action='Use this center as a benchmark for target planning and playbooks.',
                        metrics={
                            'streak_months': best_streak,
                            'year': year,
                        },
                    )
                )

    if ranked_centers:
        leader = ranked_centers[0]
        candidates.append(
            _build_insight(
                category='center_ranking',
                severity='info',
                priority=75 + leader['achievement'],
                message=f"{leader['name']} leads center ranking with {leader['achievement']}% achievement.",
                center=leader['name'],
                needs_action=False,
                action='Protect this momentum and apply the same commercial pattern elsewhere.',
                metrics={
                    'ranking': 1,
                    'achievement_pct': leader['achievement'],
                    'revenue': leader['revenue'],
                    'target': leader['target'],
                },
            )
        )

    latest_portfolio_growth = next((value for value in reversed(monthly_growth) if value is not None), None)
    if latest_month and latest_portfolio_growth is not None:
        if latest_portfolio_growth <= -8:
            candidates.append(
                _build_insight(
                    category='portfolio_growth',
                    severity='medium',
                    priority=92 + abs(latest_portfolio_growth),
                    message=f"Overall revenue declined {abs(latest_portfolio_growth)}% month over month in {latest_month}.",
                    needs_action=True,
                    action='Prioritize recovery plans for the weakest centers before month-end.',
                    metrics={
                        'month': latest_month,
                        'year': year,
                        'growth_pct': latest_portfolio_growth,
                    },
                )
            )
        elif latest_portfolio_growth >= 12:
            candidates.append(
                _build_insight(
                    category='portfolio_growth',
                    severity='info',
                    priority=72 + latest_portfolio_growth,
                    message=f"Overall revenue grew {latest_portfolio_growth}% month over month in {latest_month}.",
                    needs_action=False,
                    action='Validate whether the lift is sustainable and lock in repeatable channels.',
                    metrics={
                        'month': latest_month,
                        'year': year,
                        'growth_pct': latest_portfolio_growth,
                    },
                )
            )

    selected_items = _select_top_insights(candidates, limit=5)
    if not selected_items:
        selected_items = [
            _build_insight(
                category='portfolio_health',
                severity='info',
                priority=0,
                message='No urgent anomalies detected in the selected analytics window.',
                needs_action=False,
                action='Keep monitoring revenue, target achievement, and salary mix as new data arrives.',
            )
        ]
        selected_items[0]['rank'] = 1

    return {
        'generated_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
        'filters': {
            'year': year,
            'months': included_months,
            'latest_month': latest_month,
        },
        'summary': {
            'returned': len(selected_items),
            'limit': 5,
            'action_required': sum(1 for item in selected_items if item['needs_action']),
        },
        'items': selected_items,
    }


@analytics_bp.route('/analytics')
@login_required
def analytics():
    """Render analytics page with revenue, target, salary and achievement insights."""
    current_year = datetime.now().year
    legacy_year = request.args.get('year', current_year)

    start_month, start_year, end_month, end_year, included_periods = _sanitize_month_year_range(
        request.args.get('start_month', request.args.get('from_month', 'January')),
        request.args.get('start_year', legacy_year),
        request.args.get('end_month', request.args.get('to_month', datetime.now().strftime('%B'))),
        request.args.get('end_year', legacy_year),
    )

    included_period_set = set(included_periods)
    period_labels = [f'{month} {year}' for month, year in included_periods]

    conn = get_db()
    cur = conn.cursor()

    monthly_rows = cur.execute(
        """
        SELECT year,
               month,
               COALESCE(SUM(revenue), 0) AS total_revenue,
               COALESCE(SUM(target), 0) AS total_target
        FROM monthly_data
        WHERE year BETWEEN ? AND ?
        GROUP BY year, month
        """,
        (start_year, end_year),
    ).fetchall()

    monthly_totals = {
        (int(row['year']), row['month']): {
            'revenue': float(row['total_revenue'] or 0),
            'target': float(row['total_target'] or 0),
        }
        for row in monthly_rows
        if (row['month'], int(row['year'])) in included_period_set
    }

    salary_rows = cur.execute(
        """
        SELECT co.center_id,
               cs.coach_id,
               cs.year,
               cs.month,
               COALESCE(cs.salary, 0) AS salary
        FROM coach_salaries cs
        JOIN coaches co ON cs.coach_id = co.id
        WHERE cs.year BETWEEN ? AND ? 
          AND co.end_month IS NULL 
          AND co.end_year IS NULL
        """,
        (start_year, end_year),
    ).fetchall()

    salary_by_center_month = {}

    salary_by_center = {}
    for row in salary_rows:
        row_year = int(row['year'])
        month_name = row['month']
        if (month_name, row_year) not in included_period_set:
            continue

        cid = row['center_id']
        salary_info = calculate_final_salary_for_month(
            cur,
            coach_id=row['coach_id'],
            year=row_year,
            month_name=month_name,
            monthly_salary=float(row['salary'] or 0),
        )
        final_salary = float(salary_info['final_salary'] or 0)
        salary_by_center_month[(cid, row_year, month_name)] = salary_by_center_month.get((cid, row_year, month_name), 0.0) + final_salary
        salary_by_center[cid] = salary_by_center.get(cid, 0.0) + final_salary

    monthly_center_rows = cur.execute(
        """
        SELECT center_id,
               year,
               month,
               COALESCE(SUM(revenue), 0) AS total_revenue,
               COALESCE(SUM(target), 0) AS total_target
        FROM monthly_data
        WHERE year BETWEEN ? AND ?
        GROUP BY center_id, year, month
        """,
        (start_year, end_year),
    ).fetchall()

    monthly_center_totals = {
        (row['center_id'], int(row['year']), row['month']): {
            'revenue': float(row['total_revenue'] or 0),
            'target': float(row['total_target'] or 0),
        }
        for row in monthly_center_rows
        if (row['month'], int(row['year'])) in included_period_set
    }

    center_rows = cur.execute(
        """
        SELECT c.id,
               c.name
        FROM centers c
        ORDER BY c.name COLLATE NOCASE
        """,
    ).fetchall()

    centers = []
    for row in center_rows:
        cid = row['id']
        revenue = 0.0
        target = 0.0
        for month_name, month_year in included_periods:
            month_totals = monthly_center_totals.get((cid, month_year, month_name), {'revenue': 0.0, 'target': 0.0})
            revenue += float(month_totals['revenue'] or 0)
            target += float(month_totals['target'] or 0)

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
    target_gap = round(total_target - total_revenue, 2)
    remaining_revenue = round(max(total_target - total_revenue, 0), 2)
    achieved_revenue = round(total_revenue, 2)

    if achievement_pct > 90:
        progress_status = 'green'
    elif achievement_pct >= 70:
        progress_status = 'yellow'
    else:
        progress_status = 'red'

    avg_salary_pct = round((total_salary / total_revenue * 100) if total_revenue > 0 else 0, 1)

    ranked_centers = sorted(centers, key=lambda x: x['achievement'], reverse=True)
    best_center = ranked_centers[0]['name'] if ranked_centers else 'N/A'

    monthly_revenue = []
    monthly_target = []
    monthly_achievement = []
    monthly_growth = []
    previous_month_metrics = {}

    # For the first month, try to get previous month's revenue for growth calculation
    previous_revenue = None
    if included_periods:
        first_month, first_year = included_periods[0]
        first_month_index = CALENDAR_MONTHS.index(first_month)
        
        # If first month is not January, get previous month from same year
        if first_month_index > 0:
            prev_month = CALENDAR_MONTHS[first_month_index - 1]
            prev_year = first_year
        else:
            # If first month is January, get December from previous year
            prev_month = 'December'
            prev_year = first_year - 1
        
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

        previous_month_rows = cur.execute(
            """
            SELECT center_id,
                   COALESCE(SUM(revenue), 0) AS total_revenue,
                   COALESCE(SUM(target), 0) AS total_target
            FROM monthly_data
            WHERE year = ? AND month = ?
            GROUP BY center_id
            """,
            (prev_year, prev_month),
        ).fetchall()
        previous_month_metrics = {
            row['center_id']: {
                'revenue': float(row['total_revenue'] or 0),
                'target': float(row['total_target'] or 0),
            }
            for row in previous_month_rows
        }
    
    for month, month_year in included_periods:
        month_revenue = round(monthly_totals.get((month_year, month), {}).get('revenue', 0), 2)
        month_target = round(monthly_totals.get((month_year, month), {}).get('target', 0), 2)
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
    center_month_history = {}
    for c in centers:
        cid = c['id']
        month_achievements = []
        month_salary_pct = []
        center_month_history[cid] = {}

        for month, month_year in included_periods:
            month_label = f'{month} {month_year}'
            month_totals = monthly_center_totals.get((cid, month_year, month), {'revenue': 0.0, 'target': 0.0})
            month_revenue = float(month_totals['revenue'] or 0)
            month_target = float(month_totals['target'] or 0)
            month_salary = salary_by_center_month.get((cid, month_year, month), 0)

            month_ach = round((month_revenue / month_target * 100) if month_target > 0 else 0, 1)
            month_sal_pct = round((month_salary / month_revenue * 100) if month_revenue > 0 else 0, 1)

            center_month_history[cid][month_label] = {
                'revenue': round(month_revenue, 2),
                'target': round(month_target, 2),
                'salary': round(month_salary, 2),
                'achievement': month_ach,
                'salary_percent': month_sal_pct,
            }

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

    ai_insights = _build_ai_insights(
        year=end_year,
        included_months=period_labels,
        centers=centers,
        ranked_centers=ranked_centers,
        monthly_growth=monthly_growth,
        center_month_history=center_month_history,
        previous_month_metrics=previous_month_metrics,
    )

    center_month_series = []
    previous_month_revenue_by_center = {}
    for center in centers:
        center_id = center['id']
        center_name = center['name']
        month_history = center_month_history.get(center_id, {})
        center_month_series.append(
            {
                'center': center_name,
                'revenue': [month_history.get(month_label, {}).get('revenue', 0) for month_label in period_labels],
                'target': [month_history.get(month_label, {}).get('target', 0) for month_label in period_labels],
            }
        )
        previous_month_revenue_by_center[center_name] = round(
            float(previous_month_metrics.get(center_id, {}).get('revenue', 0) or 0),
            2,
        )

    conn.close()

    summary = {
        'total_revenue': total_revenue,
        'total_target': total_target,
        'achievement_pct': achievement_pct,
        'target_gap': target_gap,
        'remaining_revenue': remaining_revenue,
        'achieved_revenue': achieved_revenue,
        'progress_width': min(achievement_pct, 100),
        'progress_status': progress_status,
        'avg_salary_pct': avg_salary_pct,
        'best_center': best_center,
        'total_salary': total_salary,
    }

    return render_template(
        'analytics_ai.html',
        year=end_year,
        from_month=start_month,
        to_month=end_month,
        start_month=start_month,
        start_year=start_year,
        end_month=end_month,
        end_year=end_year,
        all_months=CALENDAR_MONTHS,
        all_years=list(range(current_year - 5, current_year + 2)),
        months=period_labels,
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
        ai_insights=ai_insights,
        center_month_series=center_month_series,
        previous_month_revenue_by_center=previous_month_revenue_by_center,
    )


@analytics_bp.route('/analytics/send-email-report', methods=['POST'])
@login_required
@validate_csrf
def send_analytics_email_report():
    """Send the current analytics summary as an HTML email report."""
    payload = request.get_json(silent=True) or {}

    recipients = _parse_recipients(payload.get('recipients'))
    if not recipients:
        return jsonify({'ok': False, 'error': 'Please provide at least one recipient email.'}), 400

    start_month = payload.get('start_month', payload.get('from_month', 'January'))
    start_year = payload.get('start_year', payload.get('year', datetime.now().year))
    end_month = payload.get('end_month', payload.get('to_month', datetime.now().strftime('%B')))
    end_year = payload.get('end_year', payload.get('year', datetime.now().year))
    selected_center = (payload.get('selected_center') or '').strip()

    summary = _build_email_summary_snapshot_filtered(
        start_month,
        start_year,
        end_month,
        end_year,
        selected_center=selected_center,
    )
    from_month = summary.get('start_month', start_month)
    to_month = summary.get('end_month', end_month)
    year = summary.get('end_year', _sanitize_selected_year(end_year))
    result = send_email_report(summary, year, from_month, to_month, recipients)

    status_code = 200 if result.get('ok') else 500
    return jsonify(result), status_code


@analytics_bp.route('/summer-camp-incentives')
@login_required
def summer_camp_incentives():
    """Render the summer camp incentives page with persisted revenue inputs."""
    selected_month = _sanitize_selected_month(request.args.get('month', datetime.now().strftime('%B')))
    selected_year = _sanitize_selected_year(request.args.get('year', datetime.now().year))
    selected_base_target_months = _sanitize_base_target_months(request.args.get('base_target_months'))

    conn = get_db()
    cur = conn.cursor()
    all_centers = _fetch_summer_camp_center_catalog(cur)
    rows, summary, selected_base_target_months = _build_summer_camp_payload(
        cur,
        selected_month,
        selected_year,
        selected_base_target_months,
    )
    conn.close()

    return render_template(
        'summer_camp_incentives.html',
        rows=rows,
        all_centers=all_centers,
        summary=summary,
        month=selected_month,
        year=selected_year,
        all_months=CALENDAR_MONTHS,
        selected_base_target_months=selected_base_target_months,
        default_base_target_months=SUMMER_CAMP_DEFAULT_TARGET_MONTHS,
    )


@analytics_bp.route('/summer-camp-incentives/data')
@login_required
def summer_camp_incentives_data():
    """Return Summer Camp rows and summary as JSON for dynamic filter refreshes."""
    selected_month = _sanitize_selected_month(request.args.get('month', datetime.now().strftime('%B')))
    selected_year = _sanitize_selected_year(request.args.get('year', datetime.now().year))
    selected_base_target_months = _sanitize_base_target_months(request.args.get('base_target_months'))

    conn = get_db()
    cur = conn.cursor()
    try:
        rows, summary, selected_base_target_months = _build_summer_camp_payload(
            cur,
            selected_month,
            selected_year,
            selected_base_target_months,
        )
    finally:
        conn.close()

    return jsonify(
        {
            'ok': True,
            'rows': rows,
            'summary': summary,
            'month': selected_month,
            'year': selected_year,
            'base_target_months': selected_base_target_months,
        }
    )


@analytics_bp.route('/summer-camp-incentives/save', methods=['POST'])
@login_required
@validate_csrf
def save_summer_camp_incentives():
    """Persist summer camp revenue values for the selected month and year."""
    payload = request.get_json(silent=True) or {}
    selected_month = _sanitize_selected_month(payload.get('month', datetime.now().strftime('%B')))
    selected_year = _sanitize_selected_year(payload.get('year', datetime.now().year))
    selected_base_target_months = _sanitize_base_target_months(payload.get('base_target_months'))
    submitted_rows = payload.get('rows') or []

    create_backup('summer_camp')

    conn = get_db()
    cur = conn.cursor()
    try:
        active_centers = _fetch_active_summer_camp_centers(cur)
        active_center_lookup = {
            _normalize_center_name(center_row['center']): center_row['center']
            for center_row in active_centers
        }

        for row in submitted_rows:
            incoming_name = (row.get('center') or '').strip()
            normalized_name = _normalize_center_name(incoming_name)
            center_name = active_center_lookup.get(normalized_name)
            if not center_name:
                continue

            summer_revenue = round(sanitize_number(row.get('summer_revenue'), 0), 2)
            cur.execute(
                """
                INSERT INTO summer_camp_incentives(center_name, month, year, revenue, updated_at)
                VALUES(?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(center_name, month, year)
                DO UPDATE SET revenue=excluded.revenue, updated_at=CURRENT_TIMESTAMP
                """,
                (center_name, selected_month, selected_year, summer_revenue),
            )

        conn.commit()
        rows, summary, selected_base_target_months = _build_summer_camp_payload(
            cur,
            selected_month,
            selected_year,
            selected_base_target_months,
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return jsonify(
        {
            'ok': True,
            'rows': rows,
            'summary': summary,
            'month': selected_month,
            'year': selected_year,
            'base_target_months': selected_base_target_months,
        }
    )


@analytics_bp.route('/summer-camp-incentives/centers/<int:center_id>/deactivate', methods=['POST'])
@login_required
@validate_csrf
def deactivate_summer_camp_center(center_id):
    """Hide a center from Summer Camp view without deleting it from Centers table."""
    payload = request.get_json(silent=True) or {}
    selected_month = _sanitize_selected_month(payload.get('month', datetime.now().strftime('%B')))
    selected_year = _sanitize_selected_year(payload.get('year', datetime.now().year))
    selected_base_target_months = _sanitize_base_target_months(payload.get('base_target_months'))

    conn = get_db()
    cur = conn.cursor()
    try:
        _ensure_summer_camp_center_config(cur)
        updated = cur.execute(
            """
            UPDATE summer_camp_centers_config
            SET is_active = 0,
                updated_at = CURRENT_TIMESTAMP
            WHERE center_id = ?
            """,
            (center_id,),
        )
        if updated.rowcount == 0:
            conn.rollback()
            return jsonify({'ok': False, 'message': 'Center not found.'}), 404

        conn.commit()
        rows, summary, selected_base_target_months = _build_summer_camp_payload(
            cur,
            selected_month,
            selected_year,
            selected_base_target_months,
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return jsonify(
        {
            'ok': True,
            'message': 'Center removed from this view',
            'rows': rows,
            'summary': summary,
            'month': selected_month,
            'year': selected_year,
            'base_target_months': selected_base_target_months,
        }
    )


@analytics_bp.route('/summer-camp-incentives/centers/<int:center_id>/activate', methods=['POST'])
@login_required
@validate_csrf
def activate_summer_camp_center(center_id):
    """Show a previously hidden center in Summer Camp view."""
    payload = request.get_json(silent=True) or {}
    selected_month = _sanitize_selected_month(payload.get('month', datetime.now().strftime('%B')))
    selected_year = _sanitize_selected_year(payload.get('year', datetime.now().year))
    selected_base_target_months = _sanitize_base_target_months(payload.get('base_target_months'))

    conn = get_db()
    cur = conn.cursor()
    try:
        _ensure_summer_camp_center_config(cur)
        updated = cur.execute(
            """
            UPDATE summer_camp_centers_config
            SET is_active = 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE center_id = ?
            """,
            (center_id,),
        )
        if updated.rowcount == 0:
            conn.rollback()
            return jsonify({'ok': False, 'message': 'Center not found.'}), 404

        conn.commit()
        rows, summary, selected_base_target_months = _build_summer_camp_payload(
            cur,
            selected_month,
            selected_year,
            selected_base_target_months,
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return jsonify(
        {
            'ok': True,
            'message': 'Center added back to this view',
            'rows': rows,
            'summary': summary,
            'month': selected_month,
            'year': selected_year,
            'base_target_months': selected_base_target_months,
        }
    )


@analytics_bp.route('/summer-camp-incentives/centers/restore-all', methods=['POST'])
@login_required
@validate_csrf
def restore_all_summer_camp_centers():
    """Restore all centers to active for Summer Camp view."""
    payload = request.get_json(silent=True) or {}
    selected_month = _sanitize_selected_month(payload.get('month', datetime.now().strftime('%B')))
    selected_year = _sanitize_selected_year(payload.get('year', datetime.now().year))
    selected_base_target_months = _sanitize_base_target_months(payload.get('base_target_months'))

    conn = get_db()
    cur = conn.cursor()
    try:
        _ensure_summer_camp_center_config(cur)
        cur.execute(
            """
            UPDATE summer_camp_centers_config
            SET is_active = 1,
                updated_at = CURRENT_TIMESTAMP
            """
        )
        conn.commit()
        rows, summary, selected_base_target_months = _build_summer_camp_payload(
            cur,
            selected_month,
            selected_year,
            selected_base_target_months,
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return jsonify(
        {
            'ok': True,
            'message': 'All centers restored for this view',
            'rows': rows,
            'summary': summary,
            'month': selected_month,
            'year': selected_year,
            'base_target_months': selected_base_target_months,
        }
    )


@analytics_bp.route('/summer-camp-incentives/export', methods=['POST'])
@login_required
@validate_csrf
def export_summer_camp_incentives():
    """Export Summer Camp incentive rows as a downloadable CSV file."""
    payload = request.get_json(silent=True) or {}
    selected_month = _sanitize_selected_month(payload.get('month', datetime.now().strftime('%B')))
    selected_year = _sanitize_selected_year(payload.get('year', datetime.now().year))
    selected_base_target_months = _sanitize_base_target_months(payload.get('base_target_months'))

    conn = get_db()
    cur = conn.cursor()
    try:
        rows, _summary, selected_base_target_months = _build_summer_camp_payload(
            cur,
            selected_month,
            selected_year,
            selected_base_target_months,
        )
    finally:
        conn.close()

    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(
        [
            'Center',
            'Base Target',
            '80 Percent Target',
            'Dashboard Revenue',
            'Summer Camp Revenue',
            'Total Revenue',
            'Incentive Amount',
            'Achievement Percent',
            'Status',
        ]
    )

    for row in rows:
        writer.writerow(
            [
                row.get('center', ''),
                row.get('base_target', 0),
                row.get('threshold_target', 0),
                row.get('dashboard_revenue', 0),
                row.get('summer_revenue', 0),
                row.get('total_revenue', 0),
                row.get('incentive_amount', 0),
                row.get('achievement_pct', 0),
                row.get('status_label', ''),
            ]
        )

    months_suffix = '-'.join(month[:3] for month in selected_base_target_months)
    file_name = f"summer_camp_incentives_{selected_month}_{selected_year}_{months_suffix}.csv".replace(' ', '_')
    response = make_response(csv_buffer.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename={file_name}'
    return response
