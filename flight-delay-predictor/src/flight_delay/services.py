"""
Logic and data services for the flight delay application.
API interactions, Caching, Data validation.
"""

from datetime import time
from pathlib import Path
import pandas as pd
import joblib
import streamlit as st
import requests
from flight_delay.api import aviationstack_client
from flight_delay.utils.dicts import AIRPORT_COORDS
from flight_delay.data_preprocessing import prepare_features

BASE_DIR = Path(__file__).resolve().parents[2]


@st.cache_data(ttl=1800)
def get_timetable_df(airport_code: str, timetable_type: str) -> pd.DataFrame:
    """
    Fetches flight timetable from the AviationStack API. Handles API errors.
    Results are cached for 30 minutes.
    
    :param airport_code: IATA airport code
    :type airport_code: str
    :param timetable_type: Type of the timetable to fetch ('departure'/'arrival').
    :type timetable_type: str
    :return: Flight schedule dataframe on success or an empty dataframe on failure.
    :rtype: DataFrame
    """
    try:
        raw_data = aviationstack_client.fetch_query(
            "timetable", {"iataCode": airport_code, "type": timetable_type}
        )

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
    """
    Loads the XGBoost prediction model that I have trained and saved before.
    Caches resource to only load the model once per session.

    :return: Joblib model - XGBRegressor
    """
    predictor_path = BASE_DIR / 'models' / 'flight_delay_xgb.joblib'
    return joblib.load(predictor_path)

@st.cache_data
def predict_delay(flight_row : pd.DataFrame, df : pd.DataFrame) -> int:
    """
    Calls prepare_features to preprocess the data and 
    predicts the delay if the data are in the expected format. 
    Returns the predicted delay. 
    
    :param flight_row: Row with the flight to predict on.
    :type flight_row: pd.DataFrame
    :param df: Full departure timetable.
    :type df: pd.DataFrame
    :return: The predicted delay in minutes. Rounded to the nearest integer.
    :rtype: int
    """
    x_input = prepare_features(df_departures=df, flight_row=flight_row)
    if x_input.empty:
        st.warning('Prediction failed. Error in preprocessing.')
        return None

    predictor = load_predictor()

    # XGBoost has attribute 'feature_names_in_' so this will be skipped.
    # Might be useful for future models.
    if not hasattr(predictor, 'feature_names_in_'):
        prediction = predictor.predict(x_input)[0]
        return round(float(prediction))

    predictor_features = predictor.feature_names_in_

    try:
        x_input = x_input[predictor_features]
    except KeyError as e:
        st.warning(f'Error: generated row is missing columns expected by model: {e}')
        return None

    prediction = predictor.predict(x_input)[0]

    return round(float(prediction))



def valid_flight_number(flight_num: str) -> bool:
    """
    Very simple flight number validation.

    :param flight_num: Flight number to validate
    :type flight_num: str
    :return: True if a flight is in valid format, False if it isn't.
    :rtype: bool
    """
    flight_num = flight_num.strip()
    if len(flight_num) < 2 or flight_num.isspace():
        print(len(flight_num))
        return False
    return True


def filter_flight(df: pd.DataFrame, flight_number: str) -> pd.DataFrame:
    """
    Filters the flight data from the timetable dataframe by flight number. (finds the correct row)

    :param df: Timetable dataframe.
    :type df: pd.DataFrame
    :param flight_number: Flight number to find data for.
    :type flight_number: str
    :return: Row with the data of the flight.
    :rtype: DataFrame
    """
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df['flight.iataNumber'] = df['flight.iataNumber'].fillna("").str.strip().str.upper()

    return df[df['flight.iataNumber'] == flight_number]


# Maybe fix 'time' !
def run_prediction(flight_number_input: str, flight_date_input, timetable_df: pd.DataFrame):
    """
    Whole prediction process. Filtering, Preprocessing, Predicting.
    
    :param flight_number_input: Flight number inputted by the user.
    :type flight_number_input: str
    :param flight_date_input: Date of the flight inputted by the user.
    :param timetable_df: The departure timetable.
    :type timetable_df: pd.DataFrame
    """
    flight_number = flight_number_input.strip().upper()
    date_str = flight_date_input.strftime("%Y-%m-%d")

    # DEBUG PRINTS
    print(flight_number)
    print(date_str)

    flight_df = filter_flight(timetable_df, flight_number)

    if flight_df.empty:
        st.error(f"Flight {flight_number} not found.")
        return None

    with st.spinner("Calculating delay..."):
        delay = predict_delay(flight_row=flight_df, df=timetable_df)

    return flight_df['arrival.iataCode'].iloc[0], delay, flight_number


def add_flight_for_visualization(destination_iata: str, predicted_delay: int, flight_num: str, data: list[dict]) -> list[dict]:
    """
    Updates the list of flights to be visualized on the map.
    If a previous flight to the same destination was in the list it will now be replaced by the current flight.

    :param destination_iata: Destination of the current flight.
    :type destination_iata: str
    :param predicted_delay: Current delay.
    :type predicted_delay: int
    :param flight_num: Current flight number.
    :type flight_num: str
    :param data: List of the previously predicted flights so far. Each flight is a dict with data.
    :type data: list[dict]
    :return: New list with all of the predicted flights.
    :rtype: list[dict]
    """
    prg_coords = AIRPORT_COORDS['PRG']

    if destination_iata not in AIRPORT_COORDS:
        st.warning('Cannot visualize the flight. Destination coordinates unknown.')
        return None

    destination_coords = AIRPORT_COORDS[destination_iata]

    data = [d for d in data if d['destination'] != destination_iata]

    data.append(
        {
        'destination': destination_iata, 'destination_coords': destination_coords, 
        'source_coords': prg_coords, 'predicted_delay': predicted_delay, 
        'flight_number': flight_num
        }
    )

    return data
