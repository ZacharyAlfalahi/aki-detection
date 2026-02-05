import joblib
import pandas as pd
import numpy as np

class AKIModel:
    def __init__(self, model_path, threshold):
        self.model = joblib.load(model_path)
        self.threshold = threshold
        
    def predict(self, features):
        prob = self.model.predict_proba(features)[:, 1]
        return prob >= self.threshold
    
        