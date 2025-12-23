import pandas as pd
from preprocessing import prepare_features
import joblib
import streamlit as st
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PREDICTOR_PATH = CURRENT_DIR.parent / 'models' / 'flight_delay_xgb.joblib'

@st.cache_resource
def load_predictor():
    return joblib.load(PREDICTOR_PATH)

def predict_delay(flight_row : pd.DataFrame, df : pd.DataFrame):
    Xinput = prepare_features(df_departures=df, flight_row=flight_row)
    predictor = load_predictor()

    if hasattr(predictor, "feature_names_in_"):
        predictor_features = predictor.feature_names_in_
        try:
            Xinput = Xinput[predictor_features]
        except KeyError as e:
            print(f"Error: generated row is missing columns expected by model: {e}")
            return 0

    prediction = predictor.predict(Xinput)[0]
    
    return round(float(prediction))