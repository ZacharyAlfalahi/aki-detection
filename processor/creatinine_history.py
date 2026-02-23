"""
Manages all creatinine history for patients.
"""

import csv
import logging
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)


def parse_hl7_time(timestamp):
    """Parses HL7 timestamps regardless of formatting to ensure correct ordering."""
    for fmt in ("%Y%m%d%H%M%S", "%Y%m%d%H%M", "%Y%m%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(timestamp, fmt)
        except ValueError:
            pass
    logger.warning(f"Invalid HL7 timestamp: {timestamp}")
    return None


class CreatinineHistory:
    def __init__(self):
        self.data = defaultdict(list)

    def load(self, path="./data/history.csv"):
        """Loads historical creatinine test results from wide-format CSV."""
        with open(path, newline="") as file:
            for row in csv.DictReader(file):
                mrn = row["mrn"]
                # Iterate through all 26 date/result pairs (0-25)
                for i in range(26):
                    date_key = f"creatinine_date_{i}"
                    result_key = f"creatinine_result_{i}"

                    date_val = row.get(date_key, "")
                    result_val = row.get(result_key, "")

                    # Convert empty strings to None, parse to datetime for consistency
                    timestamp = parse_hl7_time(date_val) if date_val else None
                    result = float(result_val) if result_val else None

                    self.data[mrn].append((timestamp, result))
            
    def add_reading(self, mrn, timestamp, value):
        """Insert new reading at the first empty (None, None) slot."""
        data = self.data[mrn]
        # Find first tuple with None timestamp
        for i, (ts, _) in enumerate(data):
            if ts is None:
                data[i] = (timestamp, value)
                return
        # No empty slot found, append to end
        data.append((timestamp, value))

    def add_patient(self, mrn):
        if not self.data.get(mrn):
            empty_data = [(None, None) for _ in range(26)]
            self.data[mrn] = empty_data
        return
        
    def get(self, mrn):
        return list(self.data[mrn])       