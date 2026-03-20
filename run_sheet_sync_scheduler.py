"""Run Excel sync every N seconds (default: 60)."""

import logging
import os
import time

from dotenv import load_dotenv
from excel_sync import sync_excel_to_database

load_dotenv()


def run_scheduler() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger("sheet_sync_scheduler")

    interval_seconds = int(os.environ.get("SHEET_SYNC_INTERVAL_SECONDS", "60"))
    if interval_seconds < 5:
        logger.warning("Interval too low (%s). Using 5 seconds minimum.", interval_seconds)
        interval_seconds = 5

    logger.info("Excel scheduler started. Sync interval: %s seconds", interval_seconds)

    while True:
        cycle_started = time.time()

        try:
            report = sync_excel_to_database()
            logger.info("Sync cycle completed: %s", report.as_dict())
        except Exception as exc:
            logger.exception("Sync cycle failed: %s", exc)

        elapsed = time.time() - cycle_started
        sleep_for = max(0, interval_seconds - elapsed)
        time.sleep(sleep_for)


if __name__ == "__main__":
    run_scheduler()
