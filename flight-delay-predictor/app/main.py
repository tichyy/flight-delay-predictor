import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
from flight_delay.api import aviationstack_client
from flight_delay.visualization.airport_map import show_flight_path

from interface import render_header, render_inputs, render_timetable
from services import predict_delay

def main(): 
    st.set_page_config(page_title="Flight Delay Prediction", page_icon="✈️")    
    render_header()

    if "airport_timetable" not in st.session_state:
        st.session_state.airport_timetable = {}

    if "data_cache" not in st.session_state:
        st.session_state.data_cache = {}

    if "last_flight" not in st.session_state:
        st.session_state.last_flight = None

    if "prediction_cache" not in st.session_state:
        st.session_state.prediction_cache = {}
    
    top = st.container()
    bottom = st.container()

    airport_code, flight_number = render_inputs(top, bottom)

    if flight_number != st.session_state.last_flight:
        st.session_state.pop("prediction", None)
        st.session_state.pop("prediction_error", None)
        st.session_state.pop("predicted_flight", None)
        st.session_state.last_flight = flight_number

    if top.button(f"Current timetable for **{airport_code}**"):
        if airport_code in st.session_state.data_cache:
            st.session_state.airport_timetable[airport_code] = st.session_state.data_cache[airport_code]
            # debug 
            st.toast(f"Loaded from cache!", icon="💾")
        else:
            with top:
                data = aviationstack_client.fetch_query(
                    "timetable", {"iataCode": airport_code, "type": "departure"}
                )
                st.session_state.data_cache[airport_code] = data
                st.session_state.airport_timetable[airport_code] = data

    if airport_code in st.session_state.airport_timetable:
        timetable_data = st.session_state.airport_timetable[airport_code]
        if timetable_data and "data" in timetable_data:
            timetable_df = pd.json_normalize(timetable_data["data"])
            render_timetable(timetable_df, top)

    if flight_number:
        with bottom.form("predict_form", clear_on_submit=False):
            date_input = st.date_input(
                "Flight Date",
                value=date.today(),
                min_value=date.today(),
                max_value=date.today()
            )

            submitted = st.form_submit_button(
                f"Predict delay for **{flight_number}**"
            )

        if submitted:
            # debug print
            print(flight_number)
            date_str = date_input.strftime("%Y-%m-%d")
            print(date_str)
            with st.spinner("Fetching flight data..."):
                timetable_data = None
                # try to get data from cache
                if airport_code in st.session_state.data_cache:
                    timetable_data = st.session_state.data_cache[airport_code]
                
                # if missing, fetch it and save to CACHE ONLY
                else:
                    timetable_data = aviationstack_client.fetch_query(
                        "timetable", {"iataCode": airport_code, "type": "departure"}
                    )
                    st.session_state.data_cache[airport_code] = timetable_data

                if timetable_data and "data" in timetable_data:
                    timetable_df_silent = pd.json_normalize(timetable_data["data"])
                    flight_subset = timetable_df_silent[timetable_df_silent['flight.iataNumber'].str.strip().str.upper() == flight_number.strip().upper()]
                else:
                    flight_subset = pd.DataFrame()
                # debug
                print(flight_subset[['departure.scheduledTime', 'departure.terminal', 'flight.iataNumber', 'airline.icaoCode', 'arrival.iataCode']])

            with st.spinner("Calculating delay..."):
                if flight_subset.empty:
                    # debug print
                    print(f"Flight {flight_number} not found!")
                    st.session_state.prediction_error = (
                        f"Flight {flight_number} not found!"
                    )
                else:
                    cache_key = (airport_code, flight_number, date_str)

                    if cache_key in st.session_state.prediction_cache:
                        delay = st.session_state.prediction_cache[cache_key]
                    else:
                        delay = predict_delay(flight_subset, timetable_df_silent)
                        st.session_state.prediction_cache[cache_key] = delay

                    st.session_state.prediction = delay
                    st.session_state.predicted_flight = flight_number

    if 'prediction_error' in st.session_state and st.session_state.predicted_flight == flight_number:
        st.error(st.session_state.prediction_error)
    if 'prediction' in st.session_state and st.session_state.predicted_flight == flight_number:
        st.success(f"The expected delay for **{flight_number}** is {st.session_state.prediction} minutes")

if __name__ == "__main__":
    main()