"""
Tests for src/flight_delay/ui.py
Checks behaviour for valid/wrong/empty data.
"""
import sys
from datetime import date
import pytest
import pandas as pd
from types import SimpleNamespace

class DummySpinner:
    """
    We need to mock st.spinner as an object with __enter__ and __exit methods.
    """
    def __init__(self, msg=None):
        self.msg = msg
    def __enter__(self):
        return None
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

# We will mock Streamlit because ui.py depend on it.
# Mock Streamlit generated with ChatGPT
sys.modules['streamlit'] = SimpleNamespace(
    markdown=lambda *args, **kwargs: None,
    title=lambda *args, **kwargs: None,
    caption=lambda *args, **kwargs: None,
    selectbox=lambda label, options: options[0],
    warning=lambda msg: None,
    dataframe=lambda *args, **kwargs: None,
    form=lambda id: DummySpinner(),
    text_input=lambda *args, **kwargs: 'TEST123',
    date_input=lambda *args, **kwargs: date.today(),
    form_submit_button=lambda label: True,
    columns=lambda *args, **kwargs: [DummySpinner(), DummySpinner()],
    button=lambda label: False,
    toast=lambda *args, **kwargs: None,
    session_state={},
    pills=lambda *args, **kwargs: [ 'TEST123' ],
    expander=lambda label, expanded=False: DummySpinner(),
    pydeck_chart=lambda *args, **kwargs: None,
)

# We have to import only after mocking streamlit
from flight_delay import ui


@pytest.mark.parametrize("status,expected", [
    ('ACTIVE', 'color: green;'),
    ('SCHEDULED', 'color: blue;'),
    ('LANDED', 'color: green;'),
    ('DELAYED', 'color: orange;'),
    ('CANCELLED', 'color: red;'),
    ('DIVERTED', 'color: darkorange;'),
    ('INCIDENT', 'color: darkorange;'),
    ('UNKNOWN', 'color: gray;'),
])
def test_color_status_text(status, expected):
    """
    Simple check for correct status color.
    """
    assert ui.color_status_text(status) == expected


@pytest.mark.parametrize("delay,expected", [
    (10, [0, 255, 128, 100]),
    (25, [255, 165, 0, 100]),
    (50, [255, 0, 80, 100]),
])
def test_get_arc_color(delay, expected):
    """
    Simple check for correct arc color
    """
    assert ui.get_arc_color(delay) == expected


def test_render_airport_select():
    """
    Simple check for selected airport code. (Only 'PRG' for now)
    """
    code = ui.render_airport_select()
    assert code == 'PRG'


def test_render_prediction_form():
    """
    Verify the form returns input values after submitting.
    """
    flight_number, flight_date, submitted = ui.render_prediction_form()
    assert flight_number == 'TEST123'
    assert flight_date == date.today()
    assert submitted is True


@pytest.fixture
def timetable_df():
    """
    Mock timetable fixture.
    """
    now = pd.Timestamp.now(tz='UTC')
    return pd.DataFrame({
        'departure.scheduledTime': [now + pd.Timedelta(minutes=10), now + pd.Timedelta(hours=1)],
        'flight.iataNumber': ['AB123', 'CD456'],
        'arrival.iataCode': ['FRA', 'AMS'],
        'status': ['ACTIVE', 'DELAYED'],
        'airline.name': ['Lufthansa', 'Air France']
    })

def test_render_timetable_runs(timetable_df):
    """
    Check if the timetable renders for valid input.
    """
    ui.render_timetable(timetable_df)


@pytest.fixture
def incomplete_df():
    """
    Mock incomplete df fixture.
    """
    return pd.DataFrame({
        'departure.scheduledTime': [pd.Timestamp.now(tz='UTC')],
        'flight.iataNumber': ['AB123']
    })

def test_render_timetable_missing_columns(incomplete_df):
    """
    Check if the the render_timetable doesn't fail on wrong dataframe.
    """
    ui.render_timetable(incomplete_df)

@pytest.fixture
def map_df():
    """
    Mock map dataframe fixture.
    """
    return pd.DataFrame({
        'flight_number': ['AB123', 'CD456'],
        'predicted_delay': [10, 50],
        'source_coords': [[14, 50], [4, 52]],
        'destination_coords': [[8, 50], [2, 49]],
        'destination': ['FRA', 'CDG']
    })

def test_render_map_runs(map_df):
    """
    Check for no errors in render_map, should run when provided with valid data.
    """
    ui.render_map(map_df, 'AB123')

def test_render_map_empty():
    """
    Should return None for an empty dataset, no exception.
    """
    empty_df = pd.DataFrame(columns=['flight_number','predicted_delay','source_coords','destination_coords'])
    assert ui.render_map(empty_df, 'AB123') is None

def test_render_prediction_form_not_submitted(monkeypatch):
    """
    Prediction form should correctly report submitted = False state.
    """
    monkeypatch.setattr(sys.modules['streamlit'], "form_submit_button", lambda label: False)

    _, _, submitted = ui.render_prediction_form()
    assert submitted is False
