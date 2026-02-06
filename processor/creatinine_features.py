import pandas as pd
import numpy as np

def engineer_features(age, sex, history):
    # Filter out None values and convert to floats
    valid_readings = [(t, v) for t, v in history if t is not None and v is not None]
    if not valid_readings:
        return None

    values = np.array([float(value) for _, value in valid_readings])
    times = pd.to_datetime([time for time, _ in valid_readings])

    if len(values) == 0:
        return None

    # Encode sex to match training (m=1, f=0)
    sex_encoded = 1 if str(sex).lower() == "m" else 0

    # Feature order must match training exactly
    features = {
        "age": age,
        "sex": sex_encoded,
        "creatinine_max": values.max(),
        "creatinine_min": values.min(),
        "creatinine_mean": values.mean(),
        "creatinine_std": values.std() if len(values) > 1 else 0,
        "creatinine_range": values.max() - values.min(),
        "creatinine_last": values[-1],
        "creatinine_first": values[0],
        "num_measurements": len(values),
        "measurement_span_days": (times[-1] - times[0]).days,
        "max_creatinine_increase": np.diff(values).max() if len(values) > 1 else 0
    }

    return pd.DataFrame([features])
    