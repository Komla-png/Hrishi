"""Dashboard blueprint - Main dashboard and center management routes."""

from datetime import datetime
import os
import smtplib
from io import BytesIO
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape
from flask import Blueprint, render_template, request, redirect, jsonify, flash

from models_coach_salary import calculate_final_salary_for_month
from utils import get_db, sanitize_input, login_required, CALENDAR_MONTHS, create_backup, validate_csrf

dashboard_bp = Blueprint('dashboard', __name__)


def _build_report_jpg(month, year, summary, centers, monthly_kpis, active_coach_count):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return None

    def _load_fonts():
        candidates = ['segoeui.ttf', 'arial.ttf', 'tahoma.ttf']
        for candidate in candidates:
            try:
                return {
                    'title': ImageFont.truetype(candidate, 46),
                    'subtitle': ImageFont.truetype(candidate, 26),
                    'section': ImageFont.truetype(candidate, 28),
                    'card_label': ImageFont.truetype(candidate, 20),
                    'card_value': ImageFont.truetype(candidate, 40),
                    'table_head': ImageFont.truetype(candidate, 22),
                    'table_text': ImageFont.truetype(candidate, 28),
                    'footer': ImageFont.truetype(candidate, 18),
                }
            except Exception:
                continue
        default = ImageFont.load_default()
        return {
            'title': default,
            'subtitle': default,
            'section': default,
            'card_label': default,
            'card_value': default,
            'table_head': default,
            'table_text': default,
            'footer': default,
        }

    fonts = _load_fonts()
    sorted_centers = sorted(centers, key=lambda item: item['achievement'], reverse=True)
    monthly_rows = [k for k in monthly_kpis if k.get('month') == month] or monthly_kpis

    page_width = 1800
    outer_padding = 28
    content_width = page_width - (outer_padding * 2)
    row_height = 82
    table_header_height = 72

    cards_height = 2 * 180 + 28
    centers_table_height = table_header_height + (max(1, len(sorted_centers)) * row_height)
    monthly_table_height = table_header_height + (max(1, len(monthly_rows)) * row_height)

    # Simulate y-tracking exactly to avoid footer overlap
    y_end = (
        outer_padding + 200   # header block
        + 48 + 52             # gap after header + summary section label
        + cards_height        # 2 rows × 3 cards
        + 56 + 48             # gap + center performance label
        + centers_table_height
        + 48 + 48             # gap + monthly performance label
        + monthly_table_height
    )
    page_height = max(1200, y_end + 90 + outer_padding)

    image = Image.new('RGB', (page_width, page_height), '#e2e8f0')
    draw = ImageDraw.Draw(image)
    left = outer_padding
    right = page_width - outer_padding

    # Main container
    draw.rectangle((left, outer_padding, right, page_height - outer_padding), fill='#f8fafc', outline='#cbd5e1', width=2)

    # Header
    header_bottom = outer_padding + 200
    draw.rectangle((left, outer_padding, right, header_bottom), fill='#1e3a8a')
    draw.text((left + 48, outer_padding + 56), 'Dashboard Detailed Report', fill='#f8fafc', font=fonts['title'])
    draw.text((left + 48, outer_padding + 130), f'{month} {year}', fill='#dbeafe', font=fonts['subtitle'])

    y = header_bottom + 48
    draw.text((left + 28, y), 'Summary', fill='#1e3a8a', font=fonts['section'])
    y += 52

    card_gap = 32
    card_w = (content_width - 2 * 32 - 2 * card_gap) // 3
    card_h = 180

    cards = [
        ('TOTAL REVENUE', _format_currency(summary['total_revenue'])),
        ('TOTAL TARGET', _format_currency(summary['total_target'])),
        ('ACHIEVEMENT %', f"{summary['achievement_pct']}%"),
        ('AVERAGE SALARY %', f"{summary['avg_salary_pct']}%"),
        ('BEST CENTER', summary['best_center']),
        ('ACTIVE COACHES', str(active_coach_count)),
    ]

    for i, (label, value) in enumerate(cards):
        row = i // 3
        col = i % 3
        cx = left + 22 + col * (card_w + card_gap)
        cy = y + row * (card_h + 20)
        draw.rounded_rectangle((cx, cy, cx + card_w, cy + card_h), radius=18, fill='#eef2f7', outline='#d0d7e2', width=2)
        draw.text((cx + 32, cy + 28), label, fill='#64748b', font=fonts['card_label'])
        draw.text((cx + 32, cy + 88), str(value), fill='#111827', font=fonts['card_value'])

    y += cards_height + 56
    draw.text((left + 28, y), 'Center Performance', fill='#1e3a8a', font=fonts['section'])
    y += 48

    col_x = [
        left + 32,
        left + 480,
        left + 860,
        left + 1240,
        left + 1480,
        right - 32,
    ]

    def _draw_table_header(y_top, headers):
        draw.rounded_rectangle((left + 28, y_top, right - 28, y_top + table_header_height), radius=14, fill='#0f172a')
        for i, header in enumerate(headers):
            align_right = i > 0
            if align_right:
                text_w = draw.textlength(header, font=fonts['table_head'])
                draw.text((col_x[i + 1] - 20 - text_w, y_top + 22), header, fill='#f8fafc', font=fonts['table_head'])
            else:
                draw.text((col_x[i] + 18, y_top + 22), header, fill='#f8fafc', font=fonts['table_head'])

    def _draw_row(y_top, row_data, is_even, ach_idx, sal_idx):
        bg = '#f8fafc' if is_even else '#eef2f7'
        draw.rectangle((left + 28, y_top, right - 28, y_top + row_height), fill=bg, outline='#d6dde8', width=1)
        for i, value in enumerate(row_data):
            value_text = str(value)
            color = '#1f2937'
            if i == ach_idx:
                try:
                    ach_val = float(str(value_text).replace('%', '').strip())
                except Exception:
                    ach_val = 0.0
                color = '#16a34a' if ach_val >= 100 else ('#f59e0b' if ach_val >= 80 else '#dc2626')
            if i == sal_idx:
                try:
                    sal_val = float(str(value_text).replace('%', '').strip())
                except Exception:
                    sal_val = 0.0
                color = '#dc2626' if sal_val > 30 else '#16a34a'

            if i == 0:
                draw.text((col_x[i] + 18, y_top + 26), value_text, fill=color, font=fonts['table_text'])
            else:
                text_w = draw.textlength(value_text, font=fonts['table_text'])
                draw.text((col_x[i + 1] - 20 - text_w, y_top + 26), value_text, fill=color, font=fonts['table_text'])

    _draw_table_header(y, ['Center', 'Revenue', 'Target', 'Achieved', 'Salary %'])
    y += table_header_height

    center_rows = sorted_centers or [{'name': 'N/A', 'revenue': 0, 'target': 0, 'achievement': 0, 'salary_percent': 0}]
    for idx, c in enumerate(center_rows):
        _draw_row(
            y,
            [
                c['name'],
                _format_currency(c['revenue']),
                _format_currency(c['target']),
                f"{c['achievement']}%",
                f"{c['salary_percent']}%",
            ],
            idx % 2 == 0,
            ach_idx=3,
            sal_idx=4,
        )
        y += row_height

    y += 48
    draw.text((left + 28, y), 'Monthly Performance', fill='#1e3a8a', font=fonts['section'])
    y += 48

    _draw_table_header(y, ['Month', 'Revenue', 'Target', 'Achieved', 'Salary %'])
    y += table_header_height

    month_rows = monthly_rows or [{'month': month[:3], 'total_revenue': 0, 'total_target': 0, 'achieved_percent': 0, 'salary_percent': 0}]
    for idx, m in enumerate(month_rows):
        _draw_row(
            y,
            [
                str(m['month'])[:3],
                _format_currency(m['total_revenue']),
                _format_currency(m['total_target']),
                f"{m['achieved_percent']}%",
                f"{m['salary_percent']}%",
            ],
            idx % 2 == 0,
            ach_idx=3,
            sal_idx=4,
        )
        y += row_height

    footer_y = y + 50
    generated_at = datetime.now().strftime('%d %b %Y %I:%M %p')
    draw.text((left + 36, footer_y), f'Generated on {generated_at} by Academy Dashboard.', fill='#64748b', font=fonts['footer'])

    output = BytesIO()
    image.save(output, format='JPEG', quality=90, optimize=True)
    return output.getvalue()


def _parse_recipients(raw_recipients):
    recipients = []
    for recipient in (raw_recipients or '').replace(';', ',').split(','):
        email = recipient.strip()
        if email and email not in recipients:
            recipients.append(email)
    return recipients


def _format_currency(amount):
    value = round(float(amount or 0), 2)
    if value.is_integer():
        return f'Rs {value:,.0f}'
    return f'Rs {value:,.2f}'


def _send_dashboard_email_report(payload, month, year, recipients):
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

    generated_at = datetime.now().strftime('%d %b %Y %I:%M %p')
    subject = f'Dashboard Report - {month[:3]} {year}'

    summary = payload['summary']
    centers = payload['centers']
    monthly_kpis = [k for k in payload['monthly_kpis'] if k.get('month') == month]
    active_coach_count = payload['active_coach_count']

    summary_rows = (
        ('Total Revenue', _format_currency(summary['total_revenue'])),
        ('Total Target', _format_currency(summary['total_target'])),
        ('Achievement %', f"{summary['achievement_pct']}%"),
        ('Average Salary %', f"{summary['avg_salary_pct']}%"),
        ('Best Center', escape(summary['best_center'])),
        ('Active Coaches', str(active_coach_count)),
    )

    summary_cells = [
        (
            '<td style="width:33.33%;padding:6px;vertical-align:top;">'
            '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:9px;padding:10px 12px;">'
            f'<div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.05em;">{label}</div>'
            f'<div style="font-size:18px;font-weight:700;color:#0f172a;margin-top:4px;">{value}</div>'
            '</div></td>'
        )
        for label, value in summary_rows
    ]
    summary_row1 = ''.join(summary_cells[:3])
    summary_row2 = ''.join(summary_cells[3:])

    centers_rows_html = ''
    for i, c in enumerate(sorted(centers, key=lambda item: item['achievement'], reverse=True)):
        bg = '#ffffff' if i % 2 else '#f8fafc'
        ach_color = '#16a34a' if c['achievement'] >= 100 else ('#f59e0b' if c['achievement'] >= 80 else '#dc2626')
        sal_color = '#dc2626' if c['salary_percent'] > 30 else '#16a34a'
        centers_rows_html += (
            f'<tr style="background:{bg};">'
            f'<td style="padding:7px 10px;font-size:13px;font-weight:600;">{escape(c["name"])}</td>'
            f'<td style="padding:7px 10px;text-align:right;font-size:13px;">{_format_currency(c["revenue"])}</td>'
            f'<td style="padding:7px 10px;text-align:right;font-size:13px;">{_format_currency(c["target"])}</td>'
            f'<td style="padding:7px 10px;text-align:right;font-size:13px;color:{ach_color};font-weight:700;">{c["achievement"]}%</td>'
            f'<td style="padding:7px 10px;text-align:right;font-size:13px;color:{sal_color};font-weight:700;">{c["salary_percent"]}%</td>'
            '</tr>'
        )

    monthly_rows_html = ''
    for i, k in enumerate(monthly_kpis):
        bg = '#ffffff' if i % 2 else '#f8fafc'
        ach_color = '#16a34a' if k['achieved_percent'] >= 100 else ('#f59e0b' if k['achieved_percent'] >= 80 else '#dc2626')
        monthly_rows_html += (
            f'<tr style="background:{bg};">'
            f'<td style="padding:7px 10px;font-size:13px;font-weight:600;">{escape(k["month"][:3])}</td>'
            f'<td style="padding:7px 10px;text-align:right;font-size:13px;">{_format_currency(k["total_revenue"])}</td>'
            f'<td style="padding:7px 10px;text-align:right;font-size:13px;">{_format_currency(k["total_target"])}</td>'
            f'<td style="padding:7px 10px;text-align:right;font-size:13px;color:{ach_color};font-weight:700;">{k["achieved_percent"]}%</td>'
            f'<td style="padding:7px 10px;text-align:right;font-size:13px;">{k["salary_percent"]}%</td>'
            '</tr>'
        )

    html_body = (
        '<html><body style="margin:0;background:#e2e8f0;font-family:Arial,sans-serif;color:#0f172a;">'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="padding:24px 12px;">'
        '<tr><td align="center">'
        '<table role="presentation" width="720" cellspacing="0" cellpadding="0" '
        'style="max-width:720px;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #cbd5e1;">'
        '<tr><td style="padding:20px 24px;background:linear-gradient(135deg,#0f172a,#1e3a8a);color:#f8fafc;">'
        '<div style="font-size:20px;font-weight:700;">Dashboard Detailed Report</div>'
        f'<div style="font-size:13px;opacity:.9;margin-top:6px;">{escape(month)} {year}</div>'
        '</td></tr>'
        '<tr><td style="padding:16px 16px 0;">'
        '<div style="font-size:13px;font-weight:700;color:#1e3a8a;margin-bottom:10px;">Summary</div>'
        f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr>{summary_row1}</tr><tr>{summary_row2}</tr></table>'
        '</td></tr>'
        '<tr><td style="padding:16px 16px 0;">'
        '<div style="font-size:13px;font-weight:700;color:#1e3a8a;margin-bottom:10px;">Center Performance</div>'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">'
        '<thead><tr style="background:#0f172a;color:#f8fafc;">'
        '<th style="padding:7px 10px;text-align:left;font-size:11px;">Center</th>'
        '<th style="padding:7px 10px;text-align:right;font-size:11px;">Revenue</th>'
        '<th style="padding:7px 10px;text-align:right;font-size:11px;">Target</th>'
        '<th style="padding:7px 10px;text-align:right;font-size:11px;">Achieved</th>'
        '<th style="padding:7px 10px;text-align:right;font-size:11px;">Salary %</th>'
        f'</tr></thead><tbody>{centers_rows_html}</tbody></table>'
        '</td></tr>'
        '<tr><td style="padding:16px 16px 0;">'
        '<div style="font-size:13px;font-weight:700;color:#1e3a8a;margin-bottom:10px;">Monthly Performance</div>'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">'
        '<thead><tr style="background:#0f172a;color:#f8fafc;">'
        '<th style="padding:7px 10px;text-align:left;font-size:11px;">Month</th>'
        '<th style="padding:7px 10px;text-align:right;font-size:11px;">Revenue</th>'
        '<th style="padding:7px 10px;text-align:right;font-size:11px;">Target</th>'
        '<th style="padding:7px 10px;text-align:right;font-size:11px;">Achieved</th>'
        '<th style="padding:7px 10px;text-align:right;font-size:11px;">Salary %</th>'
        f'</tr></thead><tbody>{monthly_rows_html}</tbody></table>'
        '</td></tr>'
        '<tr><td style="padding:14px 24px 20px;color:#64748b;font-size:12px;border-top:1px solid #e2e8f0;margin-top:14px;">'
        f'Generated on {generated_at} by Academy Dashboard.'
        '</td></tr>'
        '</table></td></tr></table></body></html>'
    )

    text_body = (
        f'Dashboard Detailed Report ({month} {year})\n\n'
        f"Total Revenue: {_format_currency(summary['total_revenue'])}\n"
        f"Total Target: {_format_currency(summary['total_target'])}\n"
        f"Achievement %: {summary['achievement_pct']}%\n"
        f"Average Salary %: {summary['avg_salary_pct']}%\n"
        f"Best Center: {summary['best_center']}\n"
        f'Active Coaches: {active_coach_count}\n'
    )

    report_jpg = _build_report_jpg(
        month,
        year,
        summary,
        centers,
        monthly_kpis,
        active_coach_count,
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
        file_name = f'dashboard_report_{month}_{year}.jpg'.replace(' ', '_')
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
        'message': f'Dashboard report sent to {len(recipients)} recipient(s).',
    }


def _build_dashboard_email_payload(month, year):
    conn = get_db()
    cur = conn.cursor()
    centers = _calculate_centers_data(cur, year, month)
    monthly_kpis = _calculate_monthly_kpis(cur, year)
    cur.execute(
        """
        SELECT coach_id, COALESCE(salary, 0) as salary
        FROM coach_salaries
        WHERE month = ? AND year = ?
        """,
        (month, year),
    )
    active_coach_count = 0
    for row in cur.fetchall():
        salary_info = calculate_final_salary_for_month(
            cur,
            coach_id=row["coach_id"],
            year=year,
            month_name=month,
            monthly_salary=float(row["salary"] or 0),
        )
        if salary_info["final_salary"] > 0:
            active_coach_count += 1
    conn.close()

    selected_month_kpi = next((k for k in monthly_kpis if k.get('month') == month), None)

    # Match email summary with the same KPI source used by dashboard month cards.
    if selected_month_kpi:
        total_revenue = round(float(selected_month_kpi.get('total_revenue', 0) or 0), 2)
        total_target = round(float(selected_month_kpi.get('total_target', 0) or 0), 2)
        achievement_pct = round(float(selected_month_kpi.get('achieved_percent', 0) or 0), 1)
        avg_salary_pct = round(float(selected_month_kpi.get('salary_percent', 0) or 0), 1)
    else:
        total_revenue = round(sum(c['revenue'] for c in centers), 2)
        total_target = round(sum(c['target'] for c in centers), 2)
        achievement_pct = round((total_revenue / total_target * 100) if total_target > 0 else 0, 1)
        avg_salary_pct = round((sum(c['salary_percent'] for c in centers) / len(centers)), 1) if centers else 0

    best_center = max(centers, key=lambda c: c['achievement'])['name'] if centers else 'N/A'

    return {
        'summary': {
            'total_revenue': total_revenue,
            'total_target': total_target,
            'achievement_pct': achievement_pct,
            'avg_salary_pct': avg_salary_pct,
            'best_center': best_center,
        },
        'centers': centers,
        'monthly_kpis': [selected_month_kpi] if selected_month_kpi else [],
        'active_coach_count': active_coach_count,
    }


@dashboard_bp.route("/dashboard", methods=["GET", "POST"])
@login_required

def dashboard():
    """Main dashboard view with KPIs and revenue tracking."""
    conn = get_db()
    cur = conn.cursor()
    month = request.args.get("month", datetime.now().strftime("%B"))
    year = int(request.args.get("year", datetime.now().year))
    sort = request.args.get("sort", "center")

    # ================= SAFE SAVE =================
    if request.method == "POST":
        # Auto-backup before any data modification
        create_backup("auto_dashboard")
        # ...existing code for POST unchanged...
        for key, val in request.form.items():
            if key.startswith("name"):
                cid = key.replace("name", "")
                cur.execute("UPDATE centers SET name=? WHERE id=?", (val, cid))
        cur.execute("""
            SELECT DISTINCT center_id FROM monthly_data 
            WHERE month=? AND year=?
        """, (month, year))
        centers_in_month = cur.fetchall()
        for c in centers_in_month:
            cid = c["center_id"]
            revenue_raw = request.form.get(f"revenue{cid}")
            target_raw = request.form.get(f"target{cid}")
            cur.execute("""
                SELECT revenue, target FROM monthly_data
                WHERE center_id=? AND month=? AND year=?
            """, (cid, month, year))
            existing = cur.fetchone()
            old_revenue = existing["revenue"] if existing else 0
            old_target = existing["target"] if existing else 0
            revenue = float(revenue_raw) if revenue_raw not in (None, "") else old_revenue
            target = float(target_raw) if target_raw not in (None, "") else old_target
            cur.execute("""
                UPDATE monthly_data
                SET revenue=?, target=?
                WHERE center_id=? AND month=? AND year=?
            """, (revenue, target, cid, month, year))
        conn.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            centers_data = _calculate_centers_data(cur, year, month)
            monthly_kpis = _calculate_monthly_kpis(cur, year)
            conn.close()
            return jsonify({
                "ok": True,
                "centers": centers_data,
                "monthly_kpis": monthly_kpis
            })
        return redirect(f"/dashboard?month={month}&year={year}")

    # ================= LOAD =================
    centers_data = _calculate_centers_data(cur, year, month)
    # Sort centers_data based on sort param
    if sort == "revenue":
        centers_data.sort(key=lambda x: x["revenue"], reverse=True)
    elif sort == "target":
        centers_data.sort(key=lambda x: x["target"], reverse=True)
    elif sort == "salary":
        centers_data.sort(key=lambda x: x["salary_percent"], reverse=True)
    elif sort == "achieved":
        centers_data.sort(key=lambda x: x["achievement"], reverse=True)
    else:
        centers_data.sort(key=lambda x: x["name"].lower())
    # Count only coaches with salary > 0 for the selected month/year
    cur.execute("""
        SELECT coach_id, COALESCE(salary, 0) as salary
        FROM coach_salaries
        WHERE month = ? AND year = ?
    """, (month, year))
    active_coach_count = 0
    for row in cur.fetchall():
        salary_info = calculate_final_salary_for_month(
            cur,
            coach_id=row["coach_id"],
            year=year,
            month_name=month,
            monthly_salary=float(row["salary"] or 0),
        )
        if salary_info["final_salary"] > 0:
            active_coach_count += 1

    monthly_kpis = _calculate_monthly_kpis(cur, year)
    conn.close()
    return render_template(
        "dashboard.html",
        centers=centers_data,
        month=month,
        year=year,
        monthly_kpis=monthly_kpis,
        sort=sort,
        active_coach_count=active_coach_count
    )


@dashboard_bp.route('/dashboard/send-email-report', methods=['POST'])
@login_required
@validate_csrf
def send_dashboard_email_report():
    payload = request.get_json(silent=True) or {}
    recipients = _parse_recipients(payload.get('recipients'))
    if not recipients:
        return jsonify({'ok': False, 'error': 'Please provide at least one recipient email.'}), 400

    month = payload.get('month', datetime.now().strftime('%B'))
    if month not in CALENDAR_MONTHS:
        month = datetime.now().strftime('%B')

    try:
        year = int(payload.get('year', datetime.now().year))
    except (TypeError, ValueError):
        year = datetime.now().year

    dashboard_payload = _build_dashboard_email_payload(month, year)
    result = _send_dashboard_email_report(dashboard_payload, month, year, recipients)

    status_code = 200 if result.get('ok') else 500
    return jsonify(result), status_code


def _calculate_centers_data(cur, year, month):
    """Calculate centers data with auto-target formula applied."""
    centers_data = []
    
    # Only show centers that have data for this specific month
    cur.execute("""
        SELECT c.* FROM centers c
        WHERE c.id IN (
            SELECT center_id FROM monthly_data WHERE month=? AND year=?
        )
    """, (month, year))
    centers = cur.fetchall()

    for c in centers:
        cid = c["id"]
        name = c["name"]
        
        # Apply target formula only to months that already have data for this center
        cur.execute("""
            SELECT DISTINCT month FROM monthly_data 
            WHERE center_id=? AND year=?
        """, (cid, year))
        center_months = [row["month"] for row in cur.fetchall()]
        
        for m in center_months:
            cur.execute("""
                SELECT id, revenue, target FROM monthly_data
                WHERE center_id=? AND month=? AND year=?
            """, (cid, m, year))
            md_row = cur.fetchone()
            
            cur.execute("""
                SELECT cs.coach_id, COALESCE(cs.salary, 0) as salary
                FROM coach_salaries cs
                JOIN coaches co ON cs.coach_id = co.id
                WHERE co.center_id=? AND cs.month=? AND cs.year=?
            """, (cid, m, year))
            salary_rows = cur.fetchall()
            m_salary = 0
            for salary_row in salary_rows:
                salary_info = calculate_final_salary_for_month(
                    cur,
                    coach_id=salary_row["coach_id"],
                    year=year,
                    month_name=m,
                    monthly_salary=float(salary_row["salary"] or 0),
                )
                m_salary += salary_info["final_salary"]
            
            # Auto-calculate target (salary should be <= 29.9% of target)
            calc_target = round(m_salary / 0.299, 2) if m_salary > 0 else 0
            
            if md_row and calc_target > 0:
                cur.execute("""
                    UPDATE monthly_data SET target=?
                    WHERE center_id=? AND month=? AND year=?
                """, (calc_target, cid, m, year))
        
        cur.connection.commit()

        # Get current month data for display
        cur.execute("""
            SELECT revenue, target FROM monthly_data
            WHERE center_id=? AND month=? AND year=?
        """, (cid, month, year))
        row = cur.fetchone()

        revenue = row["revenue"] if row else 0
        target = row["target"] if row else 0

        cur.execute("""
            SELECT cs.coach_id, COALESCE(cs.salary, 0) as salary
            FROM coach_salaries cs
            JOIN coaches c ON cs.coach_id = c.id
            WHERE c.center_id=? AND cs.month=? AND cs.year=?
        """, (cid, month, year))
        salary_rows = cur.fetchall()
        salary = 0
        for salary_row in salary_rows:
            salary_info = calculate_final_salary_for_month(
                cur,
                coach_id=salary_row["coach_id"],
                year=year,
                month_name=month,
                monthly_salary=float(salary_row["salary"] or 0),
            )
            salary += salary_info["final_salary"]

        achievement = (revenue / target * 100) if target > 0 else 0
        salary_percent = (salary / revenue * 100) if revenue > 0 else 0

        centers_data.append({
            "id": cid,
            "name": name,
            "revenue": revenue,
            "target": target,
            "achievement": round(achievement, 1),
            "salary_percent": round(salary_percent, 1)
        })
    
    return centers_data


def _calculate_monthly_kpis(cur, year):
    """Calculate monthly KPIs for calendar view."""
    # Aggregate total revenue and target per month
    cur.execute("""
        SELECT month, SUM(revenue) AS total_revenue, SUM(target) AS total_target
        FROM monthly_data
        WHERE year=?
        GROUP BY month
    """, (year,))
    rt_rows = cur.fetchall()

    revenue_target_by_month = {}
    for row in rt_rows:
        revenue_target_by_month[row["month"]] = {
            "total_revenue": row["total_revenue"] or 0,
            "total_target": row["total_target"] or 0,
        }

    # Aggregate total salary per month (only for coaches with valid centers)
    cur.execute("""
        SELECT cs.coach_id, cs.month, COALESCE(cs.salary, 0) AS salary
        FROM coach_salaries cs
        JOIN coaches c ON cs.coach_id = c.id
        JOIN centers ct ON c.center_id = ct.id
        WHERE cs.year=?
    """, (year,))
    sal_rows = cur.fetchall()

    salary_by_month = {m: 0 for m in CALENDAR_MONTHS}
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

    monthly_kpis = []
    for m in CALENDAR_MONTHS:
        totals = revenue_target_by_month.get(m, {"total_revenue": 0, "total_target": 0})
        total_revenue = totals["total_revenue"] or 0
        total_target = totals["total_target"] or 0
        total_salary = salary_by_month.get(m, 0) or 0

        achieved_percent = (total_revenue / total_target * 100) if total_target > 0 else 0
        salary_percent = (total_salary / total_revenue * 100) if total_revenue > 0 else 0

        monthly_kpis.append({
            "month": m,
            "total_revenue": round(total_revenue, 2),
            "total_target": round(total_target, 2),
            "achieved_percent": round(achieved_percent, 1),
            "salary_percent": round(salary_percent, 1),
        })
    
    return monthly_kpis


# ================= CENTERS MANAGEMENT =================
@dashboard_bp.route("/center/add", methods=["POST"])
@login_required

def add_center():
    """Add a new center and auto-add to all months for the year."""
    # Auto-backup before adding center
    create_backup("auto_add_center")

    name = sanitize_input(request.form.get("name")) or "New Center"
    month = request.args.get("month", datetime.now().strftime("%B"))
    year = int(request.args.get("year", datetime.now().year))

    all_months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM centers WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))", (name,))
    existing_center = cur.fetchone()
    if existing_center:
        center_id = existing_center[0]
    else:
        cur.execute("INSERT INTO centers(name) VALUES(?)", (name,))
        center_id = cur.lastrowid

    # Create monthly_data entry for all months
    for m in all_months:
        cur.execute("""
            INSERT OR IGNORE INTO monthly_data(center_id, month, year, revenue, target)
            VALUES(?, ?, ?, 0, 0)
        """, (center_id, m, year))

    conn.commit()
    conn.close()

    return redirect(f"/dashboard?month={month}&year={year}")


@dashboard_bp.route("/center/delete/<int:center_id>")
@login_required
def delete_center(center_id):
    """Delete a center and all related data (permanent)."""
    # Auto-backup before deleting center (CRITICAL!)
    create_backup("auto_delete_center")
    
    month = request.args.get("month", datetime.now().strftime("%B"))
    year = request.args.get("year", datetime.now().year)

    conn = get_db()
    cur = conn.cursor()

    # Cascade delete - removes center entirely
    cur.execute("DELETE FROM monthly_data WHERE center_id=?", (center_id,))
    cur.execute("""
        DELETE FROM coach_salaries WHERE coach_id IN 
        (SELECT id FROM coaches WHERE center_id=?)
    """, (center_id,))
    cur.execute("DELETE FROM coaches WHERE center_id=?", (center_id,))
    cur.execute("DELETE FROM centers WHERE id=?", (center_id,))

    conn.commit()
    conn.close()

    return redirect(f"/dashboard?month={month}&year={year}")


@dashboard_bp.route("/center/remove-month/<int:center_id>")
@login_required
def remove_center_month(center_id):
    """Remove center data for a specific month only (keeps center and other months)."""
    month = request.args.get("month", datetime.now().strftime("%B"))
    year = int(request.args.get("year", datetime.now().year))

    conn = get_db()
    cur = conn.cursor()
    
    # Get center name for flash message
    cur.execute("SELECT name FROM centers WHERE id=?", (center_id,))
    center_row = cur.fetchone()
    center_name = center_row[0] if center_row else "Unknown"

    # Delete only this month's revenue/target data for this center
    cur.execute("""
        DELETE FROM monthly_data 
        WHERE center_id=? AND month=? AND year=?
    """, (center_id, month, year))
    deleted_monthly = cur.rowcount

    # Delete coach salaries for this center's coaches for this month only
    cur.execute("""
        DELETE FROM coach_salaries 
        WHERE coach_id IN (SELECT id FROM coaches WHERE center_id=?)
        AND month=? AND year=?
    """, (center_id, month, year))
    deleted_salaries = cur.rowcount

    conn.commit()
    conn.close()
    
    flash(f"✅ Removed {center_name} from {month} {year} (center will still appear in other months)", "success")

    return redirect(f"/dashboard?month={month}&year={year}")
