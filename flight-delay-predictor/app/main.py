"""
Main module for my Flight Delay Prediction app.

App displays departure board, flight visualizations and predicts delays.
"""
import streamlit as st
import interface

# TODO FIX DATES IN PREDICTION FORM! (AND EVERYWHERE) AND WHEN I RUN THE APP AT 22:00 I WILL SEE TOMORROW FLIGHTS IN THE TIMETABLE!

def init_session():
    st.session_state.setdefault('timetable_df', None)
    st.session_state.setdefault('airport_code', None)

def main():
    """
    Main Streamlit app flow.
    """
    st.set_page_config(page_title="Flight Delay Prediction", page_icon="✈️")

    init_session()

    interface.render_header()

    st.session_state['airport_code'] = interface.render_airport_select()

    with st.spinner('Loading timetable...'):
        st.session_state['timetable_df'] = interface.get_timetable_df(st.session_state['airport_code'], 'departure')
    
    interface.render_refresh_button(st.session_state['airport_code'], st.session_state['timetable_df'])

    interface.render_timetable(st.session_state['timetable_df'])

    interface.render_prediction(st.session_state['timetable_df'])

if __name__ == "__main__":
    main()
