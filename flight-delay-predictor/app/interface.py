import streamlit as st
import pandas as pd

def render_header():
    st.title("Flight Delay Prediction")
    st.caption("@tichytadeas")

def render_inputs(top, bottom):
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

def render_timetable(df, pos : st.delta_generator.DeltaGenerator, limit=10):
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