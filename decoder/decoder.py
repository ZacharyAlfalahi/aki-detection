import hl7
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod

def parse_file(filename):
    with open(filename, "r") as text_file:
        raw_text = text_file.read()

    text = raw_text.replace("\n", "\r")

    return text

@dataclass
class HL7Message:
    segments: Dict[str, List[List[str]]]

    def get(self, seg: str, field_num: int) -> Optional[str]:

        fields = self.segments.get(seg)
        if not fields:
            return None
        
        return fields[field_num] if field_num < len(fields) else None

class MessageProcessor(ABC):
    @abstractmethod
    def process(self, msg: HL7Message) -> Any:
        raise NotImplementedError

class ADTA01Processor(MessageProcessor):
    def process(self, msg: HL7Message) -> dict:
        return {
            "message_type": "admit",
            "message_time": str(msg.get("MSH", 7)),
            "message_code": str(msg.get("MSH", 9)),
            "patient_id": str(msg.get("PID", 3)),
            "patient_name": str(msg.get("PID", 5)),
            "dob": str(msg.get("PID", 7)),
            "sex": str(msg.get("PID", 8)),
        }

class ADTA03Processor(MessageProcessor):
    def process(self, msg: HL7Message) -> dict:
        return {
            "message_type": "discharge",
            "message_time": str(msg.get("MSH", 7)),
            "message_code": str(msg.get("MSH", 9)),
            "patient_id": str(msg.get("PID", 3)),
        }

class ORUR01Processor(MessageProcessor):
    def process(self, msg: HL7Message) -> dict:
        return {
            "message_type": "blood_test",
            "message_time": str(msg.get("MSH", 7)),
            "message_code": str(msg.get("MSH", 9)),
            "patient_id": str(msg.get("PID", 3)),
            "result_time": str(msg.get("OBR", 7)),
            "retult_type": str(msg.get("OBX", 3)),
            "result_value": str(msg.get("OBX", 5))
        }

def parse_text(txt):

    parsed_text = hl7.parse(txt)
    msg_dict = {str(row[0]): row for row in parsed_text}
    msg_dict = HL7Message(msg_dict)
    return msg_dict

def process_message(txt):

    msg = parse_text(txt)
    _process_manual = {
        "ADT^A01": ADTA01Processor, 
        "ADT^A03": ADTA03Processor, 
        "ORU^R01": ORUR01Processor
    }

    MSH9 = str(msg.get("MSH", 9))
    processor = _process_manual.get(MSH9)()

    return processor.process(msg)

