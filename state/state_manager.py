import logging
import os
import pickle
from collections import defaultdict

logger = logging.getLogger(__name__)

STATE_DIR = "/state"


def save_state(processor):
    """Persist processor state to /state before shutdown."""
    os.makedirs(STATE_DIR, exist_ok=True)
    try:
        with open(f"{STATE_DIR}/history.pkl", "wb") as f:
            pickle.dump(dict(processor.history.data), f)

        with open(f"{STATE_DIR}/patient_info.pkl", "wb") as f:
            pickle.dump({
                "admitted": processor.patient_info.admitted,
                "details": processor.patient_info.details,
            }, f)

        with open(f"{STATE_DIR}/paged.pkl", "wb") as f:
            pickle.dump(processor.paged, f)

        logger.info("State saved to /state")
    except Exception as e:
        logger.error(f"Failed to save state: {e}")


def restore_state(processor):
    """Restore processor state from /state if available, overwriting CSV cold-start data."""
    history_path = f"{STATE_DIR}/history.pkl"
    if os.path.exists(history_path):
        try:
            with open(history_path, "rb") as f:
                processor.history.data = defaultdict(list, pickle.load(f))
            logger.info("Restored creatinine history from /state")
        except Exception as e:
            logger.error(f"Failed to restore creatinine history: {e}")

    patient_path = f"{STATE_DIR}/patient_info.pkl"
    if os.path.exists(patient_path):
        try:
            with open(patient_path, "rb") as f:
                data = pickle.load(f)
            processor.patient_info.admitted = data["admitted"]
            processor.patient_info.details = data["details"]
            logger.info("Restored patient info from /state")
        except Exception as e:
            logger.error(f"Failed to restore patient info: {e}")

    paged_path = f"{STATE_DIR}/paged.pkl"
    if os.path.exists(paged_path):
        try:
            with open(paged_path, "rb") as f:
                processor.paged = pickle.load(f)
            logger.info("Restored paged set from /state")
        except Exception as e:
            logger.error(f"Failed to restore paged set: {e}")
