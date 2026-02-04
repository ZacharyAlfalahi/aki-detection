"""
Manages all creatinine history for patients.
"""

import csv 
from collections import defaultdict, deque
from datetime import datetime

MAX_HISTORY = 50

def parse_hl7(timestamp):
    """ Parses HL7 timestamps regardless of formatting to ensure correct ordering.
    """
    for format in ("%Y%m%d%H%M%S", "%Y%m%d%H%M", "%Y%m%d"):
        try:
            return datetime.strptime(timestamp, format)
        except ValueError:
            print(f"Invalid HL7 timestamp: {timestamp}")
            

class CreatinineHistory:
    def __init__(self):
        # Only use latest 50 results per patient to limit memory usage
        self.data = defaultdict(lambda: deque(maxlen=MAX_HISTORY))
    
    def load(self, path="history.csv"):
        """ Loads historical creatinine test results, stores their values in memory, and maintains
        correct chronological order.
        """
        with open(path, newline="") as file:
            for row in csv.DictReader(file):
                mrn = row["mrn"]
                timestamp = parse_hl7(row["time"])
                value = float(row["creatinine"])
                self.data[mrn].append((timestamp, value))  
                
        for mrn in self.data:
            self.data[mrn] = deque(sorted(self.data[mrn], key=lambda x:x[0]), maxlen=MAX_HISTORY)
            
    def add(self, mrn, timestamp, value):
        self.data[mrn].append((timestamp, value))
        
    def get(self, mrn):
        return list(self.data[mrn])        
