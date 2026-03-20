"""Send dashboard + analytics email reports automatically every day at configured time."""

import json
import logging
import os
import time
import atexit
from datetime import datetime

from blueprints.analytics import _build_email_summary_snapshot, _sanitize_month_range, send_email_report
from blueprints.dashboard import _build_dashboard_email_payload, _send_dashboard_email_report

STATE_FILE = os.environ.get('DAILY_EMAIL_STATE_FILE', 'instance/daily_email_state.json')
DAILY_TIME = os.environ.get('DAILY_EMAIL_TIME', '21:00')  # 24-hour local time, default 9 PM
LOCK_FILE = os.environ.get('DAILY_EMAIL_LOCK_FILE', 'instance/daily_email_scheduler.lock')


def _parse_recipients(raw_recipients):
    recipients = []
    for recipient in (raw_recipients or '').replace(';', ',').split(','):
        email = recipient.strip()
        if email and email not in recipients:
            recipients.append(email)
    return recipients


def _load_state():
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def _save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as fh:
        json.dump(state, fh)


def _acquire_lock(logger):
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)

    while True:
        try:
            fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode('utf-8'))
            os.close(fd)
            logger.info('Scheduler lock acquired: %s', LOCK_FILE)
            return True
        except FileExistsError:
            # Check if lock is stale.
            try:
                with open(LOCK_FILE, 'r', encoding='utf-8') as fh:
                    lock_pid = int((fh.read() or '0').strip())
            except Exception:
                lock_pid = 0

            if lock_pid:
                try:
                    os.kill(lock_pid, 0)
                    logger.warning('Scheduler already running with PID %s. Exiting duplicate process.', lock_pid)
                    return False
                except OSError:
                    pass

            try:
                os.remove(LOCK_FILE)
                logger.warning('Removed stale scheduler lock file: %s', LOCK_FILE)
            except Exception:
                logger.warning('Could not remove lock file: %s', LOCK_FILE)
                return False


def _release_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception:
        pass


def _send_reports_now(logger):
    now = datetime.now()
    year = now.year
    month = now.strftime('%B')

    default_recipient = (os.environ.get('GMAIL_SMTP_USER') or '').strip()
    shared_recipients = _parse_recipients(os.environ.get('DAILY_EMAIL_RECIPIENTS', ''))
    if not shared_recipients and default_recipient:
        shared_recipients = [default_recipient]

    dashboard_recipients = _parse_recipients(os.environ.get('DASHBOARD_EMAIL_RECIPIENTS', '')) or shared_recipients
    analytics_recipients = _parse_recipients(os.environ.get('ANALYTICS_EMAIL_RECIPIENTS', '')) or shared_recipients

    dashboard_result = {'ok': False, 'error': 'No recipients configured for dashboard report.'}
    if dashboard_recipients:
        dashboard_payload = _build_dashboard_email_payload(month, year)
        dashboard_result = _send_dashboard_email_report(
            dashboard_payload,
            month,
            year,
            dashboard_recipients,
        )

    analytics_result = {'ok': False, 'error': 'No recipients configured for analytics report.'}
    if analytics_recipients:
        from_month = os.environ.get('ANALYTICS_FROM_MONTH', 'January')
        to_month = os.environ.get('ANALYTICS_TO_MONTH', month)
        from_month, to_month, included_months = _sanitize_month_range(from_month, to_month)
        summary = _build_email_summary_snapshot(year, included_months)
        analytics_result = send_email_report(
            summary,
            year,
            from_month,
            to_month,
            analytics_recipients,
        )

    logger.info('Dashboard email result: %s', dashboard_result)
    logger.info('Analytics email result: %s', analytics_result)
    return dashboard_result, analytics_result


def run_scheduler():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    logger = logging.getLogger('daily_email_scheduler')

    if ':' not in DAILY_TIME:
        raise ValueError('DAILY_EMAIL_TIME must be in HH:MM format (e.g. 21:00)')

    if not _acquire_lock(logger):
        return
    atexit.register(_release_lock)

    logger.info('Daily email scheduler started. Send time: %s (local server time)', DAILY_TIME)

    while True:
        now = datetime.now()
        now_hhmm = now.strftime('%H:%M')
        today = now.strftime('%Y-%m-%d')

        state = _load_state()
        already_sent_today = (state.get('last_sent_date') == today)

        if now_hhmm == DAILY_TIME and not already_sent_today:
            dashboard_result, analytics_result = _send_reports_now(logger)
            state['last_sent_date'] = today
            state['last_run_at'] = now.isoformat(timespec='seconds')
            state['dashboard_ok'] = bool(dashboard_result.get('ok'))
            state['analytics_ok'] = bool(analytics_result.get('ok'))
            _save_state(state)

        time.sleep(20)


if __name__ == '__main__':
    run_scheduler()
