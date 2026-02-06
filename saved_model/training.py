#!/usr/bin/env python3

""" 
AKI detection model

Train a random forest classifier to predict akute kidney injury (AKI) based on patient
demographics and historical creatinine results.
"""

import argparse
import os
import sys
import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import fbeta_score

def creatinine_features(data):
    """ Engineers features from raw training and test data.
    
    Args:
        data (pd.DataFrame): Data containing patient age, sex, AKI label, creatinine result and dates.
        
    Returns:
        pd.DataFrame: Engineered features for training.
    """
    data = data.copy()

    # Get all creatinine results and dates 
    creatinine_results = [col for col in data.columns if col.startswith("creatinine_result_")]
    creatinine_dates = [col for col in data.columns if col.startswith("creatinine_date_")]
    
    if not creatinine_results or not creatinine_dates:
        raise ValueError("No creatinine results or dates found.")
    
    for col in creatinine_dates:
        data[col] = pd.to_datetime(data[col], errors="coerce")
    
    results = data[creatinine_results]
    dates = data[creatinine_dates] 

    # Summary statistics of creatinine levels over time 
    data["creatinine_max"] = results.max(axis=1)
    data["creatinine_min"] = results.min(axis=1)
    data["creatinine_mean"] = results.mean(axis=1)
    data["creatinine_std"] = results.std(axis=1)
    data["creatinine_range"] = data["creatinine_max"] - data["creatinine_min"]
    
    # Number of measurements
    data["num_measurements"] = results.notna().sum(axis=1)
    
    # First and last measured creatinine values
    data["creatinine_first"] = results.iloc[:, 0]
    data["creatinine_last"] = results.ffill(axis=1).iloc[:,-1]
    
    # Time span between first and last measurement (in days)
    first_measurement_date = dates.iloc[:, 0]
    last_measurement_date = dates.ffill(axis=1).iloc[:,-1]
    data["measurement_span_days"] = (last_measurement_date - first_measurement_date).dt.days.fillna(0)
    
    # Largest increase between consecutive measurements
    max_increase = []
    for _, row in results.iterrows():
        values = row.dropna().values
        if len(values) > 1:
            max_increase.append(np.diff(values).max())
        else:
            max_increase.append(0)
    data["max_creatinine_increase"] = max_increase
    
    # Encode sex into binary (if missing then set as male ie 0)
    data["sex"] = data["sex"].map({"m":1, "f":0}).fillna(0)

    features = [
        "age",
        "sex", 
        "creatinine_max",
        "creatinine_min", 
        "creatinine_mean",
        "creatinine_std",
        "creatinine_range", 
        "creatinine_last",
        "creatinine_first",
        "num_measurements",
        "measurement_span_days",
        "max_creatinine_increase"
    ]

    return data[features]
    
def threshold_tuning(X, y, model, beta=3):
    """ Use stratified cross validation to tune probability threshold to maximise F3 score.
    
    Args:
        X (pd.DataFrame) 
        y (pd.Series)
        model (RandomForestClassifier) 
        beta (int): Want to maximise F3, hence beta = 3
        
    Returns:
        float : Mean optimal threshold across folds 
    """
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    thresholds = np.linspace(0.05, 0.95, 100)
    best_thresholds = []

    for train_idx, val_idx in skf.split(X, y):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
        
        model.fit(X_train, y_train)
        probs = model.predict_proba(X_val)[:, 1]
        
        results = []
        for t in thresholds:
            pred = (probs >= t).astype(int)
            f3 = fbeta_score(y_val, pred, beta=beta)
            results.append(f3)
            
        best_thresholds.append(thresholds[np.argmax(results)])
    
    return float(np.mean(best_thresholds))

def train_model(train):
    """ Train the AKI model.
    
    Args:
        train (pd.DataFrame): Training data
    
    Returns:
        model (RandomForestClassifier): Trained model
        optimal_threshold (float): Probability threshold that maximises F3 score  
    """
    X = creatinine_features(train)
    y = train["aki"].map({"y":1, "n":0})
    
    model = RandomForestClassifier(n_estimators=300, random_state=42)
        
    optimal_threshold = threshold_tuning(X, y, model)
    
    # Retrain on full data
    model.fit(X, y)

    joblib.dump(model, "model.pkl")
    joblib.dump(optimal_threshold, "threshold.pkl")
    
    return model, optimal_threshold

def test_model(test, model, optimal_threshold):
    """ Apply the trained model to test data to generate AKI predictions.

    Args:
        test (pd.DataFrame): Test data
        model (RandomForestClassifier)
        optimal_threshold (float): Probability threshold that maximises F3 score  
    
    Returns:
        list[str]: Predictions (yes or no) of whether a patient has AKI
    """
    X_test = creatinine_features(test)

    test_prob = model.predict_proba(X_test)[:,1]
    predictions = (test_prob >= optimal_threshold).astype(int)
    return ["y" if pred == 1 else "n" for pred in predictions]
    

def run_pipeline(train_path, input_path, output_path):
    """ End-to-end training and inference pipeline.
    """
    if not os.path.exists(train_path):
        sys.exit(f"Training file {train_path} not found.")
    
    if not os.path.exists(input_path):
        sys.exit(f"Test file {input_path} not found.")

    train = pd.read_csv(train_path)
    test = pd.read_csv(input_path)

    model, optimal_threshold = train_model(train)

    output = test_model(test, model, optimal_threshold)
    
    pd.DataFrame({"aki":output}).to_csv(output_path, index=False)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/test.csv")
    parser.add_argument("--output", default="data/aki.csv")
    parser.add_argument("--train", default="data/training.csv")
    
    flags = parser.parse_args()

    run_pipeline(flags.train, flags.input, flags.output)

    
if __name__ == "__main__":
    main()