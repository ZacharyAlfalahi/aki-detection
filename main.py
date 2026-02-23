import os
import signal
import sys
import logging
import joblib
from dotenv import load_dotenv
from MLLP.mllp_client import mllp_connection
from metrics.metrics import start_metrics_server
from processor.processor import Processor
from state.state_manager import save_state, restore_state

load_dotenv()

logger = logging.getLogger(__name__)

MLLP_ADDRESS = os.environ.get("MLLP_ADDRESS")


def main():
    if not MLLP_ADDRESS:
        raise ValueError("MLLP_ADDRESS environment variable not set")

    model_path = os.path.join(os.path.dirname(__file__), "saved_model", "model.pkl")
    threshold_path = os.path.join(os.path.dirname(__file__), "saved_model", "threshold.pkl")
    model = joblib.load(model_path)
    threshold = joblib.load(threshold_path)

    patient_processor = Processor(model=model, threshold=threshold)
    restore_state(patient_processor)

    processor_ref = [patient_processor]

    def handle_shutdown(signum, _frame):
        sig_name = signal.Signals(signum).name
        logger.info(f"{sig_name} received, saving state and shutting down...")
        save_state(processor_ref[0])
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    start_metrics_server(port=8000)
    logger.info("Prometheus metrics server started on port 8000")

    mllp_connection(MLLP_ADDRESS, patient_processor)


if __name__ == "__main__":
    main()
