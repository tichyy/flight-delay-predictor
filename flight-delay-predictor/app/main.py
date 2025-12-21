import streamlit as st
import pandas as pd
import numpy as np
import pydeck
from  flight_delay.api import aviationstack_client
from flight_delay.utils import db
from flight_delay.visualization.airport_map import show_flight_path
from datetime import date, datetime


def render_header():
    st.title("Flight Delay Prediction")
    st.caption("@tichytadeas")


def render_inputs(top, bottom):
    # TODO add more airports
    airports = ["Prague International Airport (PRG)"]
    airport_codes = {"Prague International Airport (PRG)" : "PRG"}
    selected_airport = top.selectbox("Deparature Airport", airports)
    flight_number = bottom.text_input("Flight Number", placeholder="e.g., AA1234")
    return airport_codes.get(selected_airport), flight_number.upper()

def color_status_text(val):
    colors = {
        "ACTIVE": "color: green;",
        "SCHEDULED": "color: blue;",
        "LANDED": "color: green;",
        "DELAYED": "color: orange;",
        "CANCELLED": "color: red;",
        "DIVERTED": "color: darkorange;",
        "INCIDENT": "color: darkorange;",
    }
    return colors.get(val, "color: gray;")

def render_timetable(df, pos : st._DeltaGenerator, limit=10):
    df = df.copy()

    df['departure.scheduledTime'] = pd.to_datetime(
        df['departure.scheduledTime'], utc=True, errors="coerce"
    )

    now = pd.Timestamp.now(tz="UTC")
    df = df[df['departure.scheduledTime'] >= now]
    df = df[df['flight.iataNumber'].notna() & (df['flight.iataNumber'].str.strip() != "")]

    df['Scheduled Time'] = df['departure.scheduledTime'].dt.strftime('%H:%M')
    df['Status'] = df['status'].str.upper()
    df['Airline'] = df['airline.name']
    df['Flight Number'] = df['flight.iataNumber']
    df['Destination Airport'] = df['arrival.iataCode']

    df_render = df[['Status', 'Scheduled Time', 'Flight Number', 'Airline', 'Destination Airport']]


    df_styled = df_render.style.map(
        color_status_text, subset=["Status"], 
    ).set_table_styles([
        {"selector": "thead", "props": [("background-color", "#f0f0f0"), ("color", "#000") ]},
        {"selector": "tbody", "props": [("background-color", "#ffffff"), ("color", "#000") ]},
        {"selector": "th", "props": [("color", "#000") ]},
        {"selector": "td", "props": [("color", "#000") ]}
    ]).hide(axis="index")

    pos.markdown("Departures Board")
    pos.dataframe(
        df_styled,
        width="stretch",
        hide_index=True,
    )

def fetch_flight_data(flight_number: str):
    """
    Fetch flight info for a given flight number and date
    Returns a normalized DataFrame with flight info.
    """
    query = {
        'dep_iata' : 'PRG', 
        'flight_iata': flight_number
    }
    response = aviationstack_client.fetch_query("flights", query)
    if not response or "data" not in response:
        # debug
        print("NOT RESPONDING")
        return None
    df = pd.json_normalize(response["data"])
    return df


def main(): 
    if "airport_timetable" not in st.session_state:
        st.session_state.airport_timetable = {}

    st.set_page_config(page_title="Flight Delay Prediction", page_icon="✈️")    
    render_header()
    
    top = st.container()
    bottom = st.container()

    airport_code, flight_number = render_inputs(top, bottom)
    airport_timetables = { "PRG" : 0 }
    
    # TODO Add a flight map for the selected airport

    if top.button(f"Current timetable for **{airport_code}**"):
        with top:
            st.session_state.airport_timetable[airport_code] = aviationstack_client.fetch_query(
                "timetable", {"iataCode": airport_code, "type": "departure"}
            )

    if airport_code in st.session_state.airport_timetable:
        timetable_data = st.session_state.airport_timetable[airport_code]
        if timetable_data and "data" in timetable_data:
            df = pd.json_normalize(timetable_data["data"])
            render_timetable(df, top)

    if flight_number:
        date_input = bottom.date_input("Flight Date", value=date.today(), min_value=date.today(), max_value=date.today())
        date_str = date_input.strftime("%Y-%m-%d")
        if bottom.button(f"Predict delay for **{flight_number}**"):
            print(flight_number)
            print(date_str)
            with st.spinner("Fetching flight data..."):
                flight_df = fetch_flight_data(flight_number)
                render_timetable(flight_df, top)
                with st.spinner("Calculating delay..."):
                    # TODO Predict delay
                    pass
                st.success("Prediction completed!")


if __name__ == "__main__":
    main()