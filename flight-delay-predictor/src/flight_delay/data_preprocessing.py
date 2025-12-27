"""
This module contains the complete data preprocessing for the flight prediction ML model.
It prepares wanted features including external weather and airport traffic data.
"""

import json
from pathlib import Path
import pandas as pd
import requests
import numpy as np
import streamlit as st
from flight_delay.api import aviationstack_client
from flight_delay.utils.dicts import SCHENGEN_AIRPORTS


BASE_DIR = Path(__file__).resolve().parents[2]


def prepare_features(df_departures : pd.DataFrame, flight_row : pd.DataFrame, one_hot = False) -> pd.DataFrame:
    """
    Preprocesses a raw flight row into a dataframe with specific features for the ML model.
    Feature engineering - Adds traffic information (departures/arrivals). Adds weather data.
    Cyclical features for day of week and hour.
    
    :param df_departures: Full departure timetable. 
    :type df_departures: pd.DataFrame
    :param flight_row: Row with the flight we want to predict on.
    :type flight_row: pd.DataFrame
    :param one_hot: True for One Hot Encoding, False for Label Encoding.
    :return: Row with processed features or empty dataframe if the preprocessing fails.
    :rtype: DataFrame
    """
    df_departures = df_departures.copy()

    schengen_airports = SCHENGEN_AIRPORTS

    flight_row = flight_row[[
        'departure.terminal',
        'departure.delay',
        'departure.scheduledTime',
        'airline.icaoCode',
        'departure.actualTime',
        'arrival.iataCode'
    ]]

    flight_row = flight_row.rename(columns={
        'departure.terminal': 'terminal',
        'departure.delay': 'delay',
        'departure.scheduledTime': 'scheduled_time',
        'airline.icaoCode': 'airline',
        'departure.actualTime': 'actual_time',
        'arrival.iataCode': 'destination_airport'
    })

    if pd.isna(flight_row['scheduled_time'].iloc[0]):
        flight_row = flight_row.replace(flight_row['scheduled_time'], flight_row['actual_time'])

    flight_row['scheduled_time'] = pd.to_datetime(flight_row['scheduled_time'])
    flight_row['actual_time'] = pd.to_datetime(flight_row['actual_time'])

    flight_row = add_traffic(df_departures, flight_row)

    flight_row = add_weather(flight_row)

    # Convert scheduled_time to columns that are relevant for ML
    flight_row['day_of_week'] = flight_row['scheduled_time'].dt.weekday
    flight_row['day_in_month'] = flight_row['scheduled_time'].dt.day
    flight_row['hour'] = flight_row['scheduled_time'].dt.round('h').dt.hour

    flight_row.drop(columns=['scheduled_time'], inplace=True)

    # cyclical features
    # hours
    flight_row['hour_sin'] = np.sin(2 * np.pi * flight_row['hour'] / 24)
    flight_row['hour_cos'] = np.cos(2 * np.pi * flight_row['hour'] / 24)
    flight_row.drop(columns=['hour'],inplace=True)
    # day of week
    flight_row['weekday_sin'] = np.sin(2 * np.pi * flight_row['day_of_week'] / 7)
    flight_row['weekday_cos'] = np.cos(2 * np.pi * flight_row['day_of_week'] / 7)
    flight_row.drop(columns=['day_of_week'],inplace=True)

    # print(flight_row.columns)

    with open(BASE_DIR/'data'/'processed'/'fill_values.json', 'r', encoding='utf-8') as f:
        fill_values = json.load(f)

    flight_row = flight_row.fillna(value=fill_values).infer_objects(copy=False)

    flight_row.drop(columns='actual_time', inplace=True)

    if pd.isna(flight_row['terminal'].iloc[0]):
        if flight_row['destination_airport'].iloc[0] in schengen_airports:
            flight_row['terminal'] = 2
        else:
            flight_row['terminal'] = 1

    categorical = ['terminal', 'airline', 'destination_airport']

    with open(BASE_DIR/'data'/'processed'/'categories.json', 'r', encoding='utf-8') as f:
        categories = json.load(f)

    # for col in flight_row.columns:
    #     print(f'{col} : {flight_row[col].iloc[0]}')

    categories['destination_airport'] = [airport.upper() for airport in categories['destination_airport']]
    categories['airline'] = [airline.upper() for airline in categories['airline']]

    if not one_hot:
        for col in categorical:
            cat_type = pd.api.types.CategoricalDtype(
                categories=categories[col],
                ordered=False
            )
            flight_row[col] = flight_row[col].astype(cat_type).cat.codes

    # DEBUGGING TABLE
    # summary = pd.DataFrame({
    #     'Dtype': flight_row.dtypes,
    #     'Unique': flight_row.nunique(),
    #     'NaN': flight_row.isnull().sum(),
    #     'Zeros': (flight_row == 0).sum()
    # })

    # print(summary)

    # DEBUGGING PRINT
    # for col in flight_row.columns:
    #     print(f'{col} : {flight_row[col].iloc[0]}')

    # Might change this later.
    # Currently we are ignoring the 'delay' displayed by the airport.
    flight_row.drop(columns='delay', inplace=True)

    if flight_row.isnull().sum().sum() == 0:
        return flight_row

    return pd.DataFrame()


@st.cache_data(ttl=1800)
def get_weather() -> pd.DataFrame:
    """
    Fetches the weather forecast for PRG airport from the Open-Meteo API.
    Results are cached for 30 minutes.
    
    :return: Hourly weather data for today.
    :rtype: DataFrame
    """
    prg_lat = 50.1008
    prg_lon = 14.2600

    url = 'https://api.open-meteo.com/v1/forecast'
    params = {
        'latitude': prg_lat,
        'longitude': prg_lon,
        'hourly': 'temperature_2m,precipitation,wind_speed_10m',
        'wind_speed_unit': 'kmh',
        'timezone': 'Europe/Prague',
        'forecast_days': 1
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        # parse the hourly data
        hourly = data['hourly']
        df_weather = pd.DataFrame({
            'time': pd.to_datetime(hourly['time']),
            'temp_c': hourly['temperature_2m'],
            'precip_mm': hourly['precipitation'],
            'wind_kph': hourly['wind_speed_10m']
        })

    except Exception as e:
        st.warning(f'Weather API Failed: {e}. Using fallback values for weather.')
        return pd.DataFrame()
    return df_weather


def add_weather(flight_row : pd.DataFrame) -> pd.DataFrame:
    """
    Adds the weather features to the flight row. If no hour bucket matches, fills features with NaNs.
    
    :param flight_row: Row with the flight data.
    :type flight_row: pd.DataFrame
    :return: Row with added weather features.
    :rtype: DataFrame
    """

    flight_hour = flight_row['scheduled_time'].dt.round('h').iloc[0]

    df_weather = get_weather()

    match = df_weather[df_weather['time'] == flight_hour]

    if not match.empty:
        # Assign values to the flight_row
        flight_row['temp_c'] = match.iloc[0]['temp_c']
        flight_row['precip_mm'] = match.iloc[0]['precip_mm']
        flight_row['wind_kph'] = match.iloc[0]['wind_kph']
    else:
        flight_row['temp_c'] = np.nan
        flight_row['precip_mm'] = np.nan
        flight_row['wind_kph'] = np.nan

    return flight_row


@st.cache_data(ttl=1800)
def get_arrival_df() -> pd.DataFrame:
    """
    Fetches the arrival timetable for PRG airport. Uses AviationStack API.
    Caches data for 30 minutes.    

    :return: Timetable with arrivals
    :rtype: DataFrame
    """
    try:
        df_arrivals = aviationstack_client.fetch_query(
            'timetable', {'iataCode': 'PRG', 'type': 'arrival'}
        )

        df_arrivals = pd.json_normalize(df_arrivals['data'])

        df_arrivals['arrival.scheduledTime'] = pd.to_datetime(df_arrivals['arrival.scheduledTime'])

        df_arrivals['hour_bucket'] = df_arrivals['arrival.scheduledTime'].dt.round('h')

        return df_arrivals
    except Exception as e:
        print(f'API failed ({e}). Using fallback value for ARRIVAL TRAFFIC.')
        return pd.DataFrame()


def add_traffic(df_departures: pd.DataFrame, flight_row: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates airport traffic features for the specific time window. 
    Adds the traffic features to the flight row.  

    :param df_departures: Timetable with departures.
    :type df_departures: pd.DataFrame
    :param flight_row: Row with the flight we are predicting on.
    :type flight_row: pd.DataFrame
    :return: Row with added traffic features.
    :rtype: DataFrame
    """
    # Departures
    flight_time = flight_row['scheduled_time'].dt.round('h').iloc[0]

    df_departures['departure.scheduledTime'] = pd.to_datetime(df_departures['departure.scheduledTime'])

    df_departures['hour_bucket'] = df_departures['departure.scheduledTime'].dt.round('h')

    # Departure traffic is all the departuring flights in the same hour bucket - 1 for the flight that we are predicting
    flight_row['departure_traffic'] = (df_departures['hour_bucket'] == flight_time).sum() - 1

    df_arrivals = get_arrival_df()

    if not df_arrivals.empty:
        # Arrival traffic is all the arriving flights in the same hour bucket
        flight_row['arrival_traffic'] = (df_arrivals['hour_bucket'] == flight_time).sum()
    else:
        # np.nan so the column gets filled later with the fallback value
        flight_row['arrival_traffic'] = np.nan

    return flight_row
