import streamlit as st
import pandas as pd
from services import prediction_logic, get_timetable_df, valid_flight_number
from datetime import date
from flight_delay.utils.dicts import AIRPORT_COORDS
import pydeck as pdk

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
    st.title('Flight Delay Prediction')
    st.caption('@tichytadeas')

def render_airport_select():
    # TODO Add more airports.
    airports = ['Prague International Airport (PRG)']
    airport_codes = {'Prague International Airport (PRG)' : 'PRG'}
    selected_airport = st.selectbox('Departure Airport', airports)
    return airport_codes.get(selected_airport)

def color_status_text(val):
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
    if df.empty:
        st.warning('Timetable rendering failed. Timetable is empty.')
        return

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

    df['departure.scheduledTime'] = pd.to_datetime(df['departure.scheduledTime'], utc=True, errors='coerce')

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

def get_arc_color(delay):
    if delay < 20:
        return [0, 255, 128, 100]
    elif delay < 45:
        return [255, 165, 0, 100]
    else:
        return [255, 0, 80, 100]

@st.fragment
def render_flight_visualization(destination_iata, predicted_delay, flight_num, data):
    prg_coords = AIRPORT_COORDS['PRG']

    if destination_iata not in AIRPORT_COORDS:
        st.warning('Cannot visualize the flight. Destination coordinates unknown.')
        return 
    
    destination_coords = AIRPORT_COORDS[destination_iata]

    data = [d for d in data if d['destination'] != destination_iata]

    data.append(
        {
        'destination': destination_iata, 'destination_coords': destination_coords, 
        'source_coords': prg_coords, 'predicted_delay': predicted_delay, 
        'flight_number': flight_num
        }
    )
    
    df = pd.DataFrame(data)


    with st.expander("Map Controls", expanded=False):
        all_flights = df['flight_number'].unique().tolist()
        
        shown_flights = st.pills("Select flights to show:", options=all_flights, default=all_flights, selection_mode='multi')
        
        if not shown_flights:
            st.warning(f"⚠ At least one flight must be visible. Showing flight: {flight_num}.")
            
            shown_flights = [flight_num]

        df = df[df['flight_number'].isin(shown_flights)]

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
        "html": "<b> Flight number: </b> {flight_number} <br/> <b>Destination:</b> {destination} <br/> <b>Predicted Delay:</b> {predicted_delay} mins",
        "style": {"backgroundColor": "steelblue", "color": "white"}
    }

    st.pydeck_chart(pdk.Deck(
        map_style='https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
        initial_view_state=view_state,
        layers=[arc_layer],
        tooltip=tooltip
    ))

    return data


@st.fragment
def render_prediction(timetable_df):
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

    if not submitted:
        return

    if not valid_flight_number(flight_number_input):
        st.error('Enter a valid flight number!')
        return

    destination_iata, predicted_delay, flight_num = prediction_logic(flight_number_input, flight_date_input, timetable_df)

    st.session_state['predicted_flights'] = render_flight_visualization(destination_iata, predicted_delay, flight_num, st.session_state['predicted_flights'])


def render_refresh_button(airport_code, timetable_df):
    if st.button(f'Refresh timetable for **{airport_code}**'):
        get_timetable_df.clear()
        new_timetable_df = get_timetable_df(airport_code=airport_code, timetable_type='departure')
        if new_timetable_df.equals(timetable_df):
            st.toast('Timetable is already up-to-date!', icon='✔️', duration=2)
        if not new_timetable_df.empty:    
            st.session_state['timetable_df'] = new_timetable_df
