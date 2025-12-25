import pandas as pd
from preprocessing import prepare_features
import joblib
import streamlit as st
from pathlib import Path
from flight_delay.api import aviationstack_client
import requests

CURRENT_DIR = Path(__file__).resolve().parent
PREDICTOR_PATH = CURRENT_DIR.parent / 'models' / 'flight_delay_xgb.joblib'

@st.cache_data(ttl=1800)
def get_timetable_df(airport_code: str, timetable_type: str) -> pd.DataFrame:
    try:
        raw_data = aviationstack_client.fetch_query("timetable", {"iataCode": airport_code, "type": timetable_type})

    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 429:
            st.error('Too many requests. Try again in 1 minute.')
        else:
            print(f'status code: {e.response.status_code}')
            st.error('Something went wrong. Try again later.')
            print(f'HTTP error fetching timetable for "{airport_code}" "{timetable_type}": {e}')
        return pd.DataFrame()
    except Exception as e:
        st.error('Something went wrong. Try again later.')
        print(f'Exception raised when fetching timetable for "{airport_code}" "{timetable_type}": {e}')
        return pd.DataFrame()

    if not raw_data or 'data' not in raw_data:
        return pd.DataFrame()

    return pd.json_normalize(raw_data['data'])

@st.cache_resource
def load_predictor():
    return joblib.load(PREDICTOR_PATH)


def predict_delay(flight_row : pd.DataFrame, df : pd.DataFrame):
    Xinput = prepare_features(df_departures=df, flight_row=flight_row)
    predictor = load_predictor()

    if not hasattr(predictor, 'feature_names_in_'):
        prediction = predictor.predict(Xinput)[0]
        return round(float(prediction))

    predictor_features = predictor.feature_names_in_

    try:
        Xinput = Xinput[predictor_features]
    except KeyError as e:
        print(f'Error: generated row is missing columns expected by model: {e}')
        return 0

    prediction = predictor.predict(Xinput)[0]
    
    return round(float(prediction))


@st.cache_data
def predict_delay_cached(flight_row: pd.DataFrame, df: pd.DataFrame, flight_num: str, date: str) -> int: 
    return predict_delay(flight_row=flight_row, df=df)

def valid_flight_number(flight_num: str) -> bool:
    if len(flight_num) < 2 or flight_num.isspace():
        print(len(flight_num))
        return False
    return True

def filter_flight(df: pd.DataFrame, flight_number: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    
    df = df.copy()
    df['flight.iataNumber'] = df['flight.iataNumber'].fillna("").str.strip().str.upper()

    return df[df['flight.iataNumber'] == flight_number]

def prediction_logic(flight_number_input, flight_date_input, timetable_df):
    if not valid_flight_number(flight_number_input):
        st.error('Enter a valid flight number!')
        return
    
    flight_number = flight_number_input.strip().upper()
    date_str = flight_date_input.strftime("%Y-%m-%d")

    flight_df = filter_flight(timetable_df, flight_number)

    if flight_df.empty:
        st.error(f"Flight {flight_number} not found.")
        return

    with st.spinner("Calculating delay..."):
        delay = predict_delay_cached(
            flight_row=flight_df,
            df=timetable_df,
            flight_num=flight_number,
            date=date_str,
        )

    st.success(
        f"The expected delay for **{flight_number}** is {delay} minutes"
    )