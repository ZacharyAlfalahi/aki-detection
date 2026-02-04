"""
Tracks whether a patient is currently in hospital.

Admitting a patient is represented by message type: ADT^A01.
Discharging a patient is represented by message type: ADT^A03.
"""

class PatientState:
    def __init__(self):
        self.admitted = {}
        
    def admit(self, mrn):
        self.admitted[mrn] = True
        
    def discharge(self, mrn):
        self.admitted [mrn] = False
    
    # If never seen this patient, assign 'not admitted'
    def status(self, mrn):
        return self.admitted.get(mrn, False)