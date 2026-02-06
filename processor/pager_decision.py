"""
Container for the outcome of processing a single HL7 event.
"""

from dataclasses import dataclass

@dataclass
class PagerDecision:
    # Whether we send an HTTP POST
    page: bool 
    
    # Patient identifier (PID.3)
    mrn: str = None 
    
    # Test result time (OBR.7)
    timestamp: str = None
    
    # Human readable explanation (for logs)
    reason: str = ""