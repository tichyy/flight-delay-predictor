import streamlit as st
import pandas as pd
import pydeck
from  flight_delay.api import aviationstack_client
from flight_delay.utils import db
from flight_delay.visualization.airport_map import show_flight_path


def render_header():
    st.title("Flight Delay Prediction")
    st.caption("@tichytadeas")


def render_inputs(top, bottom):
    # More airports might be added in the future
    airports = ["Prague International Airport (PRG)"]
    airport_codes = {"Prague International Airport (PRG)" : "PRG"}
    selected_airport = top.selectbox("Deparature Airport", airports)
    flight_number = bottom.text_input("Flight Number", placeholder="e.g., AA1234")
    return airport_codes.get(selected_airport), flight_number.upper()


def render_timetable(df, pos : st._DeltaGenerator):
    pos.dataframe(df) 
    # TODO


def main(): 
    st.set_page_config(page_title="Flight Delay Prediction", page_icon="✈️")    
    render_header()
    
    top = st.container()
    bottom = st.container()

    airport_code, flight_number = render_inputs(top, bottom)
    airport_timetables = { "PRG" : 0 }
    
    # TODO Add a flight map for the selected airport

    if top.button(f"Current timetable for **{airport_code}**"):
        with top:
            airport_timetables[airport_code] = aviationstack_client.fetch_query("timetable", {"iataCode" : airport_code, "type" : "departure"})
        if airport_timetables[airport_code]:
            df = pd.json_normalize(airport_timetables[airport_code]["data"])
            render_timetable(df, top)

    if top.button(f"**{airport_code}** Airport map"):
        # TODO Visualization
        pass

    if flight_number and bottom.button(f"Predict delay for **{flight_number}**"):
        with st.spinner("Calculating delay..."):
            show_flight_path(flight_number)
            # TODO Predict delay
            pass
        st.success("Prediction completed!")


if __name__ == "__main__":
    main()