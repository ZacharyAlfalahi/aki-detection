"""
Tracks patient admission status and demographics.

Combines functionality from patient_state.py and patient_details.py.
"""

from datetime import datetime
class PatientInfo:
    """Unified tracker for patient admission status and demographics."""

    def __init__(self):
        self.admitted: dict[str, bool] = {}
        self.details: dict[str, dict] = {}

    def admit(self, mrn, dob, sex):
        """Record patient admission with demographics.

        Args:
            mrn: Medical record number
            dob: Date of birth in YYYYMMDD format
            sex: Patient sex ('m' or 'f')
        """
        self.admitted[mrn] = True

        # Calculate age from DOB
        birth_date = datetime.strptime(dob, "%Y%m%d")
        today = datetime.today()
        age = today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )
        self.details[mrn] = {"age": age, "sex": sex}

    def discharge(self, mrn):
        """Record patient discharge."""
        self.admitted[mrn] = False

    def is_admitted(self, mrn):
        """Check if patient is currently admitted."""
        return self.admitted.get(mrn, False)

    def get_details(self, mrn):
        """Get patient demographics (age, sex)."""
        return self.details.get(mrn, {"age": None, "sex": None})
