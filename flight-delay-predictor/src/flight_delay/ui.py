"""
User interface components and rendering logic for the flight delay prediction application.
Layout, Buttons, Input handling, Visualization
"""

from datetime import date
import streamlit as st
import pandas as pd
import pydeck as pdk
from flight_delay.services import get_timetable_df

st.markdown(
    '''
    <style>
    .block-container {
        padding-top: 1rem;
    }
    </style>
    ''',
    unsafe_allow_html=True
)

def render_header():
    """
    Renders the header and caption.
    """
    st.title('Flight Delay Prediction')
    st.caption('@tichytadeas')

def render_airport_select() -> str:
    """
    Renders a selectbox for choosing the departure airport. 
    There is only 'PRG' airport. I made this function for better scalability.

    :return: IATA code of the selected airport
    :rtype: str
    """
    # Scaling: Add more airports.
    airports = ['Prague International Airport (PRG)']
    airport_codes = {'Prague International Airport (PRG)' : 'PRG'}
    selected_airport = st.selectbox('Departure Airport', airports)
    return airport_codes.get(selected_airport)

def color_status_text(val: str) -> str:
    """
    Function chooses a color for each flight status.
    
    :param val: The status of the flight (df['status'])
    :type val: str
    :return: Color for the status cell in the timetable
    :rtype: str
    """
    colors = {
        'ACTIVE': 'color: green;',
        'SCHEDULED': 'color: blue;',
        'LANDED': 'color: green;',
        'DELAYED': 'color: orange;',
        'CANCELLED': 'color: red;',
        'DIVERTED': 'color: darkorange;',
        'INCIDENT': 'color: darkorange;',
    }
    return colors.get(val, 'color: gray;')


def render_timetable(df : pd.DataFrame):
    """
    Processes the timetable dataframe and renders departure table.
    Displays only todays flights that has not left yet.
    
    :param df: Raw timetable dataframe
    :type df: pd.DataFrame
    """
    required_cols = [
        'departure.scheduledTime',
        'flight.iataNumber',
        'arrival.iataCode',
        'status',
        'airline.name'
    ]

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.warning('Timetable rendering failed. Dataframe is missing some required columns.')
        return

    df = df.copy()

    df['departure.scheduledTime'] = pd.to_datetime(
        df['departure.scheduledTime'], utc=True, errors='coerce'
    )

    now = pd.Timestamp.now(tz='UTC')
    df = df[df['departure.scheduledTime'] >= now]

    # only todays flights
    df = df[df['departure.scheduledTime'].dt.date == date.today()]
    df = df[df['flight.iataNumber'].notna() & (df['flight.iataNumber'].str.strip() != '')]

    df['Scheduled Time'] = df['departure.scheduledTime'].dt.strftime('%H:%M')
    df['Status'] = df['status'].str.upper()
    df['Airline'] = df['airline.name']
    df['Flight Number'] = df['flight.iataNumber']
    df['Destination Airport'] = df['arrival.iataCode']


    df_render = df[['Status', 'Scheduled Time', 'Flight Number', 'Airline', 'Destination Airport']]

    df_styled = df_render.style.map(
        color_status_text, subset=['Status'],
    ).set_table_styles([
        {'selector': 'thead', 'props': [('background-color', '#f0f0f0'), ('color', '#000') ]},
        {'selector': 'tbody', 'props': [('background-color', '#ffffff'), ('color', '#000') ]},
        {'selector': 'th', 'props': [('color', '#000') ]},
        {'selector': 'td', 'props': [('color', '#000') ]}
    ]).hide(axis='index')

    st.markdown('Departures Board')
    st.dataframe(
        df_styled,
        width='stretch',
        hide_index=True,
        height=300
    )

def get_arc_color(delay: int) -> list[int]:
    """
    Chooses a color based on the delay.
        
    :param delay: Predicted delay in minutes
    :type delay: int
    :return: Color in RGBA format
    :rtype: list[int]
    """
    if delay < 20:
        return [0, 255, 128, 100]
    if delay < 45:
        return [255, 165, 0, 100]
    return [255, 0, 80, 100]


def render_map(df: pd.DataFrame, flight_num: str):
    """
    Renders a PyDeck map with flight paths.
    Also renders a st.pills in an st.expander to filter which flights to show on the map. 
    
    :param df: Dataframe with predicted flight details. (coordinates, delay)
    :type df: pd.DataFrame
    :param flight_num: Latest (current) predicted flight number.
    :type flight_num: str
    """
    if df.empty:
        return
    
    with st.expander("Map Controls", expanded=False):
        all_flights = df['flight_number'].unique().tolist()

        shown_flights = st.pills(
            "Select flights to show:",
            options=all_flights,
            default=all_flights,
            selection_mode='multi'
        )

        if not shown_flights:
            st.warning(f"⚠ At least one flight must be visible. Showing flight: {flight_num}.")

            shown_flights = [flight_num]

        df = df[df['flight_number'].isin(shown_flights)]

    df = df.copy()

    df['color'] = df['predicted_delay'].apply(get_arc_color)

    arc_layer = pdk.Layer(
        'ArcLayer',
        data=df,
        get_source_position='source_coords',
        get_target_position='destination_coords',
        get_source_color='color',
        get_target_color='color',
        get_width=4,
        get_height=0.5,
        pickable=True,
        auto_highlight=True
    )

    view_state = pdk.ViewState(
        latitude=45.0,
        longitude=20.0,
        zoom=3.5,
        pitch=30,
        bearing=0
    )

    tooltip = {
        "html": "<b> Flight number: </b> {flight_number} <br/> "
        "<b>Destination:</b> {destination} <br/> "
        "<b>Predicted Delay:</b> {predicted_delay} mins",
        "style": {"backgroundColor": "steelblue", "color": "white"}
    }

    st.pydeck_chart(pdk.Deck(
        map_style='https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
        initial_view_state=view_state,
        layers=[arc_layer],
        tooltip=tooltip
    ))


def render_prediction_form():
    """
    Renders the form for inputting flight number and date for the prediction.
    
    So far only todays flights are allowed because I am using free APIs. 
    Added the date column for better scalability.
    """
    with st.form('flight_predict_form'):
        c1, c2 = st.columns([2, 1])

        with c1:
            flight_number_input = st.text_input(
                label='Flight Number', placeholder='e.g. AB1234'
            )

        with c2:
            flight_date_input = st.date_input(
                label='Flight Date',
                value=date.today(),
                max_value=date.today(),
                min_value=date.today(),
            )

        submitted = st.form_submit_button('Predict delay')
    return flight_number_input, flight_date_input, submitted


def render_refresh_button(airport_code: str, timetable_df: pd.DataFrame):
    """
    Renders a button to refresh the flight timetable data.
    
    After clicking it clears the cache, fetches new data and updates the session state.

    :param airport_code: IATA code of the selected airport.
    :type airport_code: str
    :param timetable_df: Current timetable (before refreshing).
    :type timetable_df: pd.DataFrame
    """
    if st.button(f'Refresh timetable for **{airport_code}**'):
        get_timetable_df.clear()
        new_timetable_df = get_timetable_df(airport_code=airport_code, timetable_type='departure')
        if new_timetable_df.equals(timetable_df):
            st.toast('Timetable is already up-to-date!', icon='✔️', duration=2)
        if not new_timetable_df.empty:
            st.session_state['timetable_df'] = new_timetable_df
