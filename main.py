import streamlit as st
import pandas as pd
import src

def render_header():
    st.title("Flight Delay Prediction")
    st.caption("@tichytadeas")


def render_inputs(top, bottom):
    airports = ["Prague International Airport (PRG)", "Frankfurt Airport (FRA)", "Vienna International Airport (VIE)"]
    airport_codes = {"Prague International Airport (PRG)" : "PRG", "Frankfurt Airport (FRA)" : "FRA", "Vienna International Airport (VIE)" : "VIE"}
    selected_airport = top.selectbox("Deparature Airport", airports)
    flight_number = bottom.text_input("Flight Number", placeholder="e.g., AA1234")
    return airport_codes.get(selected_airport), flight_number.upper()

def render_timetable(df, pos : st._DeltaGenerator):
    pos.dataframe(df) 
    # TODO Update as soon as possible


def main():
    st.set_page_config(page_title="Flight Delay Prediction", page_icon="✈️")    
    render_header()
    
    top = st.container()
    bottom = st.container()

    airport_code, flight_number = render_inputs(top, bottom)
    
    # TODO Add a flight map for the selected airport

    if top.button(f"Current timetable for **{airport_code}**"):
        with top:
            timetable_json = src.fetch_query("timetable", {"iataCode" : airport_code, "type" : "departure"})
        if timetable_json:
            df = pd.json_normalize(timetable_json["data"])
        render_timetable(df, top)

    if flight_number and bottom.button(f"Predict delay for **{flight_number}**"):
        with st.spinner("Calculating delay..."):
            # TODO Predict delay
            pass
        st.success("Prediction completed!")


if __name__ == "__main__":
    main()