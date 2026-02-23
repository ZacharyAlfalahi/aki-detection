import os
import signal
import sys
import logging
from dotenv import load_dotenv
from MLLP.mllp_client import mllp_connection
from metrics.metrics import start_metrics_server

load_dotenv()

logger = logging.getLogger(__name__)

PAGER_ADDRESS = os.environ.get("PAGER_ADDRESS")
MLLP_ADDRESS = os.environ.get("MLLP_ADDRESS")


def handle_shutdown(signum, frame):
    sig_name = signal.Signals(signum).name
    logger.info(f"{sig_name} received, shutting down gracefully...")
    sys.exit(0)


def main():
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    if not MLLP_ADDRESS:
        raise ValueError("MLLP_ADDRESS environment variable not set")

    start_metrics_server(port=8000)
    logger.info("Prometheus metrics server started on port 8000")

    mllp_connection(MLLP_ADDRESS)


if __name__ == "__main__":
    main()
