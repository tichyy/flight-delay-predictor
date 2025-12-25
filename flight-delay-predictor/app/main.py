from interface import render_header, render_airport_select, render_timetable, render_prediction, render_refresh_button
from services import get_timetable_df
    
def main(): 
    render_header()

    airport_code = render_airport_select()
    timetable_df = get_timetable_df(airport_code=airport_code, timetable_type='departure')

    render_refresh_button(airport_code=airport_code, timetable_df=timetable_df)

    render_timetable(df=timetable_df)

    render_prediction(timetable_df=timetable_df)

if __name__ == "__main__":
    main()