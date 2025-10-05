import streamlit as st

def render_header():
    st.title("Flight Delay Prediction")
    st.caption("@tichytadeas")


def render_inputs(top, bottom):
    airports = ["Prague International Airport (PRG)", "Frankfurt Airport (FRA)", "Vienna International Airport (VIE)"]
    selected_airport = top.selectbox("Deparature Airport", airports)
    flight_number = bottom.text_input("Flight Number", placeholder="e.g., AA1234")
    return selected_airport, flight_number.upper()


def main():
    st.set_page_config(page_title="Flight Delay Prediction", page_icon="✈️")    
    render_header()
    
    top = st.container()
    bottom = st.container()

    airport, flight_number = render_inputs(top, bottom)
    
    # TODO Add a flight map for the selected airport

    if top.button(f"Current timetable for **{airport}**"):
        # TODO Display timetable
        pass

    if flight_number and bottom.button(f"Predict delay for **{flight_number}**"):
        with st.spinner("Calculating delay..."):
            # TODO Predict delay
            pass
        st.success("Prediction completed!")


if __name__ == "__main__":
    main()