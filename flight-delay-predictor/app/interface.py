import streamlit as st
import pandas as pd
from services import prediction_logic, get_timetable_df
from datetime import date

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

def render_header():
    st.set_page_config(page_title="Flight Delay Prediction", page_icon="✈️")    
    st.title("Flight Delay Prediction")
    st.caption("@tichytadeas")

def render_airport_select():
    airports = ["Prague International Airport (PRG)"]
    airport_codes = {"Prague International Airport (PRG)" : "PRG"}
    selected_airport = st.selectbox("Deparature Airport", airports)
    return airport_codes.get(selected_airport)


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


def render_timetable(df : pd.DataFrame):
    if df.empty:
        print('Timetable rendering failed. Dataframe is empty.')
        return

    required_cols = [
        "departure.scheduledTime",
        "flight.iataNumber",
        "arrival.iataCode"
    ]

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print('Timetable rendering failed. Dataframe is missing some required columns.')
        return
    
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

    st.markdown("Departures Board")
    st.dataframe(
        df_styled,
        width="stretch",
        hide_index=True,
        height=300
    )


@st.fragment
def render_prediction(timetable_df):
    with st.form("flight_predict_form"):
        c1, c2 = st.columns([2, 1])

        with c1:
            flight_number_input = st.text_input(
                label="Flight Number", placeholder="e.g. AB1234"
            )

        with c2:
            flight_date_input = st.date_input(
                label="Flight Date",
                value=date.today(),
                max_value=date.today(),
                min_value=date.today(),
            )

        submitted = st.form_submit_button("Predict delay")

    if not submitted:
        return

    prediction_logic(flight_number_input, flight_date_input, timetable_df)

def render_refresh_button(airport_code, timetable_df):
    if st.button(f"Refresh timetable for **{airport_code}**"):
        get_timetable_df.clear()
        new_timetable_df = get_timetable_df(airport_code=airport_code, timetable_type='departure')
        if new_timetable_df.equals(timetable_df):
            st.toast('Timetable is already up-to-date!', icon='✔️', duration=2)
        if not new_timetable_df.empty:
            timetable_df = new_timetable_df