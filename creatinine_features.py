import pandas as pd
import numpy as np

def engineer_features(age, sex, history):
    values = np.array([value for _, value in history])
    times = pd.to_datetime([time for time, _ in history])
    
    if len(values) == 0:
        return None
    
    # Same engineered features as in training from CW 1
    features = {
        "age": age,
        "sex": sex,
        "creatinine_max": values.max(),
        "creatinine_min": values.min(),
        "creatinine_mean": values.mean(),
        "creatinine_std": values.std() if len(values) > 1 else 0,
        "creatinine_range": values.max() - values.min(),
        "creatinine_first": values[0],
        "creatinine_last": values[-1],
        "num_measurements": len(values),
        "measurement_span_days": (times.iloc[-1] - times.iloc[0]).days,
        "max_creatinine_increase": np.diff(values).max() if len(values) > 1 else 0
    }
    
    return pd.DataFrame([features])
    