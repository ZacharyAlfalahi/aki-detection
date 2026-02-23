import logging
import os
import time
import requests
from dotenv import load_dotenv
from metrics.metrics import PAGER_REQUESTS, PAGER_ERRORS, PAGER_ALERTS_DROPPED

load_dotenv()

logger = logging.getLogger(__name__)

PAGER_ADDRESS = os.environ.get("PAGER_ADDRESS")

MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 0.5  # seconds
MAX_RETRY_DELAY = 1  # seconds


def page_hospital(mrn, test_time, pager_url=PAGER_ADDRESS):
    payload = f"{mrn},{test_time}"

    if not pager_url.startswith(('http://', 'https://')):
        pager_url = f"http://{pager_url}"

    url = f"{pager_url.rstrip('/')}/page"
    retry_delay = INITIAL_RETRY_DELAY

    for attempt in range(MAX_RETRIES):
        try:
            PAGER_REQUESTS.inc()
            r = requests.post(
                url,
                data=payload,
                headers={"Content-Type": "text/plain"},
                timeout=1,
            )
            r.raise_for_status()
            return

        except requests.exceptions.HTTPError as e:
            PAGER_ERRORS.inc()
            logger.error(f"Pager HTTP error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")

        except requests.exceptions.ConnectionError as e:
            PAGER_ERRORS.inc()
            logger.error(f"Pager connection error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")

        except requests.exceptions.Timeout as e:
            PAGER_ERRORS.inc()
            logger.error(f"Pager timeout (attempt {attempt + 1}/{MAX_RETRIES}): {e}")

        if attempt < MAX_RETRIES - 1:
            logger.info(f"Retrying pager in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)

    PAGER_ALERTS_DROPPED.inc()
    logger.error(f"Pager failed after {MAX_RETRIES} attempts for MRN {mrn}")
