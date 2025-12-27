"""
Main entry point for my Flight Delay Prediction app.
App displays departure board, flight visualizations and predicts delays.
"""

import streamlit as st
import pandas as pd
import ui
from flight_delay import services


def init_session():
    """
    Initializes the Streamlit session state variables.
    """
    st.session_state.setdefault('timetable_df', None)
    st.session_state.setdefault('airport_code', None)
    st.session_state.setdefault('predicted_flights', [])


def visualization(destination_iata: str, predicted_delay: int, flight_num: str):
    """
    Updates the session state with a new flight prediction and renders the map.
    
    :param destination_iata: IATA code of the destination airport
    :type destination_iata: str
    :param predicted_delay: Predicted delay in minutes.
    :type predicted_delay: int
    :param flight_num: Flight Number
    :type flight_num: str
    """
    st.session_state['predicted_flights'] = services.add_flight_for_visualization(
        destination_iata, predicted_delay, flight_num, st.session_state['predicted_flights']
    )

    data = pd.DataFrame(st.session_state['predicted_flights'])

    ui.render_map(data, flight_num)


@st.fragment()
def prediction():
    """
    Manages the prediction workflow: input, validation, logic and result display.

    This function runs as a Streamlit fragment to minimize full app reruns.
    """
    flight_number_input, flight_date_input, submitted = ui.render_prediction_form()
    if not submitted:
        return

    if not services.valid_flight_number(flight_number_input):
        st.error('Enter a valid flight number!')
        return

    destination_iata, predicted_delay, flight_num = services.run_prediction(
        flight_number_input, flight_date_input, st.session_state['timetable_df']
    )

    st.success(
        f'The expected delay for **{flight_num}** is {predicted_delay} minutes'
    )

    visualization(destination_iata, predicted_delay, flight_num)


def main():
    """
    Main entry point for my Streamlit app. 
    Flow of the app.
    """
    st.set_page_config(page_title="Flight Delay Prediction", page_icon="✈️")

    init_session()

    ui.render_header()

    st.session_state['airport_code'] = ui.render_airport_select()

    with st.spinner('Loading timetable...'):
        st.session_state['timetable_df'] = ui.get_timetable_df(
            st.session_state['airport_code'], 'departure'
        )

    if st.session_state['timetable_df'].empty:
        st.warning('Timetable rendering failed. Timetable is empty.')
    else:
        ui.render_timetable(st.session_state['timetable_df'])

    ui.render_refresh_button(st.session_state['airport_code'], st.session_state['timetable_df'])

    prediction()


if __name__ == "__main__":
    main()
