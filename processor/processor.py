import logging
import os
import pandas as pd
from typing import Optional
from .pager_decision import PagerDecision
from .creatinine_history import CreatinineHistory, parse_hl7_time
from .patient_info import PatientInfo
from .creatinine_features import engineer_features
from pager.pager import page_hospital
from metrics.metrics import BLOOD_TESTS_RECEIVED, AKI_PREDICTIONS_TOTAL, AKI_POSITIVE_PREDICTIONS, BLOOD_TEST_VALUES

logger = logging.getLogger(__name__)


def _predict_aki(model, threshold, features):
    """Make AKI prediction using model and threshold."""
    prob = model.predict_proba(features)[:, 1]
    return bool(prob[0] >= threshold)


class Processor:
    def __init__(
        self,
        model,
        threshold: float,
        cre_history: Optional[CreatinineHistory] = None,
        patient_info: Optional[PatientInfo] = None
    ):
        self.model = model
        self.threshold = threshold
        self.patient_info = patient_info if patient_info is not None else PatientInfo()
        self.paged = set()

        if cre_history is not None:
            self.history = cre_history
        else:
            self.history = CreatinineHistory()
            history_path = "/data/history.csv"
            if not os.path.exists(history_path):
                history_path = "./data/history.csv"
            try:
                self.history.load(history_path)
                logger.info(f"Loaded history from {history_path}")
            except FileNotFoundError:
                logger.warning("No history file found, starting with empty history")

    def process_event(self, event):
        """Handles one message (decides whether to page and updates patient history)."""
        msg_type = event["type"]
        mrn = event.get("mrn")

        # Patient admission
        if msg_type == "ADT^A01":
            sex = event["sex"]
            dob = event["dob"]
            self.patient_info.admit(mrn, dob, sex)
            return PagerDecision(page=False, reason="admitted")

        # Patient discharge
        if msg_type == "ADT^A03":
            self.patient_info.discharge(mrn)
            return PagerDecision(page=False, reason="discharged")

        # Lab result
        if msg_type == "ORU^R01":
            # Check test type
            if event["test_type"] != "CREATININE":
                return PagerDecision(page=False, reason="invalid test type")

            BLOOD_TESTS_RECEIVED.inc()

            # Update patient's creatinine history
            value = event["test_value"]
            try:
                BLOOD_TEST_VALUES.observe(float(value))
            except (ValueError, TypeError):
                pass
            test_time = event["test_time"]
            timestamp = parse_hl7_time(test_time)

            self.history.add_reading(mrn, timestamp, value)
            hist = self.history.get(mrn)

            details = self.patient_info.get_details(mrn)
            age = details["age"]
            sex = details["sex"]

            # Need multiple valid measurements to infer
            valid_count = sum(1 for t, v in hist if t is not None and v is not None)
            if valid_count < 2:
                return PagerDecision(page=False, reason="insufficient history")

            # Check for duplicate pages
            if (mrn, test_time) in self.paged:
                return PagerDecision(page=False, reason="duplicate")

            # Engineer creatinine features
            features = engineer_features(age=age, sex=sex, history=hist)
            if features is None:
                return PagerDecision(page=False, reason="feature engineering failed")

            # Run model prediction
            aki = _predict_aki(self.model, self.threshold, features)
            AKI_PREDICTIONS_TOTAL.inc()

            if aki:
                AKI_POSITIVE_PREDICTIONS.inc()
                self.paged.add((mrn, test_time))
                page_hospital(mrn, test_time)
                return PagerDecision(page=True, mrn=mrn, timestamp=test_time, reason="AKI detected")

            return PagerDecision(page=False, reason="no AKI detected")

        return PagerDecision(page=False, reason=f"unknown message type: {msg_type}")
