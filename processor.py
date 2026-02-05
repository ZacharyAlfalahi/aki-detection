from .pager_decision import PagerDecision
from .creatinine_features import engineer_features
from .creatinine_history import parse_hl7

class Processor:
    def __init__(self, history, state, model):
        self.history = history
        self.state = state
        self.model = model
        self.paged = set()
        
    def process_event(self, event):
        """ Handles one message (ie decides whether to page or not, and updates patient history)
        """
        type = event["type"]
        test_type = event["test_type"]
        mrn = event.get("mrn")

        # Checks patient status 
        if type == "ADT_A01":
            self.state.admit(mrn)
            return PagerDecision(page=False, reason="admitted")

        if type == "ADT_A03":
            self.state.discharge(mrn)
            return PagerDecision(page=False, reason="discharged")
        
        if not self.state.status(mrn):
            return PagerDecision(page=False, reason="not admitted")

        # Checks type of test conducted 
        if test_type != "CREATININE" or type != "ORU_R01":
            return PagerDecision(page=False, reason="invalid test type")

        # Update patients creatinine history
        value = event["test_value"]
        test_time = event["test_time"]
        timestamp = parse_hl7(test_time)

        self.history.add(mrn, timestamp, value)
        hist = self.history.get(mrn)

        # Need multiple measurements to infer 
        if len(hist) < 2:
            return PagerDecision(page=False, reason="insufficient history")

        # Checked for repeated paged messages
        if (mrn, test_time) in self.paged:
            return PagerDecision(False, reason="duplicate")

        # Engineer creatinine features
        features = engineer_features(age=event["age"], sex=event["sex"], history=hist)
        if features is None:
            return PagerDecision(page=False)
        
        # Run model
        aki = self.model.predict(features)[0]

        if aki:
            self.paged.add((mrn, test_time))
            return PagerDecision(True, mrn, test_time, "AKI detected")

        return PagerDecision(False)
    
    # Need event to have agreed keys (type, test_type etc) and PagerDecision to have agreed fields 