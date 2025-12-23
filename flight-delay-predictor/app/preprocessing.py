import pandas as pd
import requests
import numpy as np
import json
from pathlib import Path
from flight_delay.api import aviationstack_client
import streamlit as st


CURRENT_DIR = Path(__file__).resolve().parent

def prepare_features(df_departures : pd.DataFrame, flight_row : pd.DataFrame, one_hot = False):

    df_departures = df_departures.copy()
    
    schengen_airports = [
        'fra','waw','zrh','cdg','bgy','arn','brq','muc','ams','vie','bcn','edi',
        'ltn','rmf','hel','mxp','tfs','bru','ksc','agp','gla','lgw','dus','rix',
        'mad','dub','tuf','poz','lis','tia','gdn','sll','otp','alc','sof','bwe',
        'klu','pmi','nap','cph','beg','ein','nte','snu','fnc','blq','ath','stn',
        'bud','vlc','flr','kut','ayt','ncl','tsf','cta','rho','ema','rns','gro',
        'bri','ory','osr','lba','tbs','opo','spu','psa','crl','cia','ktt','psr',
        'lcy','lca','bio','lux','cag','lys','cgn','lpa','tat','gva','bsl','rkt',
        'nqz','kef','klx','lpl','prg','fue','vod','skg','bva','bhx','svq','pdl',
        'lbg','igs','krk','haj','got','bvc','mrs','lin','gyd','rmo','bah','var',
        'bfs','nce','ber','smv','ktw','vce','trs','her','inn','dla','mla','pqc',
        'pmo','str','ped','rmi','fao','cfu','rtm','bts','zad','sbz','hog','ala',
        'qzp','kbv','cvf','szg','kun','bqh','qrs','trn','adb','sir','asr','erf',
        'nue','zag','pfo','ndr','wro','qiu','grz','aey','lej','plq','ham','tsr',
        'peg','vrn','sma','qky','bll','sco','mct','pow','xry','tln','fae','bjz',
        'rze','mmx','ghv'
    ]
    
    random_seed = 333

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

    print(flight_row.columns)

    with open(CURRENT_DIR.parent/'data'/'processed'/'fill_values.json', 'r') as f:
        FILL_VALUES = json.load(f)

    flight_row = flight_row.fillna(value=FILL_VALUES)

    flight_row.drop(columns='actual_time', inplace=True)

    if pd.isna(flight_row['terminal'].iloc[0]):
        if flight_row['destination_airport'].iloc[0] in schengen_airports:
            flight_row['terminal'] = 2
        else:
            flight_row['terminal'] = 1

    categorical = ['terminal', 'airline', 'destination_airport']

    with open(CURRENT_DIR.parent/'data'/'processed'/'categories.json', 'r') as f:
        CATEGORIES = json.load(f)

    for col in flight_row.columns:
        print(f'{col} : {flight_row[col].iloc[0]}')

    CATEGORIES['destination_airport'] = [airport.upper() for airport in CATEGORIES['destination_airport']]
    CATEGORIES['airline'] = [airline.upper() for airline in CATEGORIES['airline']]

    if not one_hot:
        for col in categorical:
            cat_type = pd.api.types.CategoricalDtype(
                categories=CATEGORIES[col],
                ordered=False
            )
            flight_row[col] = flight_row[col].astype(cat_type).cat.codes

    # debug prints
    # summary = pd.DataFrame({
    #     'Dtype': flight_row.dtypes,
    #     'Unique': flight_row.nunique(),
    #     'NaN': flight_row.isnull().sum(),
    #     'Zeros': (flight_row == 0).sum()
    # })

    # print(summary)
    for col in flight_row.columns:
        print(f'{col} : {flight_row[col].iloc[0]}')

    # TODO change later
    flight_row.drop(columns='delay', inplace=True)

    if flight_row.isnull().sum().sum() == 0:
        return flight_row
    else:
        return None

@st.cache_resource
def get_weather():
    LAT = 50.1008
    LON = 14.2600

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": "temperature_2m,precipitation,wind_speed_10m",
        "wind_speed_unit": "kmh",
        "timezone": "Europe/Prague",
        "forecast_days": 1
    }
    df_weather = None
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
        print(f"Weather API Failed: {e}")
    return df_weather


def add_weather(flight_row : pd.DataFrame) -> pd.DataFrame:
    LAT = 50.1008
    LON = 14.2600
    
    flight_hour = flight_row['scheduled_time'].dt.round('h').iloc[0]

    df_weather = get_weather()

    match = df_weather[df_weather['time'] == flight_hour]
        
    if not match.empty:
        # Assign values to the flight_row
        flight_row['temp_c'] = match.iloc[0]['temp_c']
        flight_row['precip_mm'] = match.iloc[0]['precip_mm']
        flight_row['wind_kph'] = match.iloc[0]['wind_kph']
    else:
        print(f"Error. Used weather fallback!")
        flight_row['temp_c'] = np.nan
        flight_row['precip_mm'] = np.nan
        flight_row['wind_kph'] = np.nan

    return flight_row



def add_traffic(df_departures, flight_row):
    # Departures
    df_departures['departure.scheduledTime'] = pd.to_datetime(df_departures['departure.scheduledTime'])

    df_departures['hour_bucket'] = df_departures['departure.scheduledTime'].dt.round('h')
    
    my_time = flight_row['scheduled_time'].dt.round('h').iloc[0]

    flight_row['departure_traffic'] = (df_departures['hour_bucket'] == my_time).sum() - 1

    try:
        df_arrivals = aviationstack_client.fetch_query(
            "timetable", {"iataCode": 'PRG', "type": "arrival"}
        )

        df_arrivals = pd.json_normalize(df_arrivals["data"])

        df_arrivals['arrival.scheduledTime'] = pd.to_datetime(df_arrivals['arrival.scheduledTime'])

        df_arrivals['hour_bucket'] = df_arrivals['arrival.scheduledTime'].dt.round('h')

        flight_row['arrival_traffic'] = (df_departures['hour_bucket'] == my_time).sum()
        
    except Exception as e:
        print(f"Warning: API failed ({e}). Using fallback traffic value.")
        flight_row['arrival_traffic'] = np.nan

    return flight_row