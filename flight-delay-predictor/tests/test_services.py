"""
Tests for src/flight_delay/services.py
"""
import sys
from types import SimpleNamespace
import pytest
import pandas as pd

class DummySpinner:
    """
    We need to mock st.spinner as an object with __enter__ and __exit methods.
    """
    def __init__(self, msg=None):
        """
        __init__
        """
        self.msg = msg
    def __enter__(self):
        """
        Mock __enter__ method
        """
        return None
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Mock __exit__ method
        """
        return False

# We need to mock Streamlit because services.py depend on it.
# Mock Streamlit generated with ChatGPT
sys.modules['streamlit'] = SimpleNamespace(
    cache_data=lambda ttl=None: lambda f: f,
    cache_resource=lambda f: lambda f2: f2,
    warning=lambda msg: None,
    error=lambda msg: None,
    spinner=lambda msg: DummySpinner(msg),
)


from flight_delay import services

@pytest.fixture
def mock_timetable_df():
    """
    Mock timetable data.
    """
    return pd.DataFrame({
        'flight.iataNumber': ["LH123", "LH124", "AF456", "BA789"],
        'arrival.iataCode': ["FRA", "AMS", "CDG", "LHR"]
    })


@pytest.fixture
def mock_predict_delay(monkeypatch):
    """
    Mock predict_delay function to return a constant. (42)
    """
    monkeypatch.setattr("flight_delay.services.predict_delay", lambda flight_row, df: 42)
    yield


@pytest.mark.parametrize("flight_num,expected", [
    ("LH123", True),
    (" ", False),
    ("A", False),
    ("AF456", True),
    ("BA789", True),
    ("XYZ", True),
    ("lh123", True),
    ("LH 123", False),
])
def test_valid_flight_number(flight_num, expected):
    """
    Test return values for valid and invalid inputs.
    """
    assert services.valid_flight_number(flight_num) == expected


@pytest.mark.parametrize("flight_number,expected_len", [
    ("LH123", 1),
    ("LH124", 1),
    ("AF456", 1),
    ("BA789", 1),
    ("UNKNOWN", 0),
    ("", 0),
    (None, 0),
])
def test_filter_flight(flight_number, expected_len, mock_timetable_df):
    """
    Test if the filter_flight function returns correct number of rows.
    """
    filtered = services.filter_flight(mock_timetable_df, flight_number)
    assert len(filtered) == expected_len


@pytest.mark.parametrize("flight_number_input,expected_dest,expected_delay", [
    ("LH123", "FRA", 42),
    ("AF456", "CDG", 42),
    ("BA789", "LHR", 42),
])
def test_run_prediction(mock_predict_delay, mock_timetable_df, flight_number_input, expected_dest, expected_delay):
    """
    Test the run_prediction function.
    """
    result = services.run_prediction(flight_number_input, pd.Timestamp("2025-12-26"), mock_timetable_df)
    assert result is not None
    dest, delay, flight_number = result
    assert dest == expected_dest
    assert delay == expected_delay
    assert flight_number == flight_number_input


@pytest.mark.parametrize("flight_number_input", [
    "",
    " ",
    "INVALID",
    "LH999", # not in the mock timetable
])
def test_run_prediction_invalid_inputs(mock_predict_delay, mock_timetable_df, flight_number_input):
    """
    Test invalid inputs for run_prediction.
    """
    result = services.run_prediction(
        flight_number_input,
        pd.Timestamp("2025-12-26"),
        mock_timetable_df
    )
    assert result is None


@pytest.mark.parametrize("destination_iata,prev_flights,new_delay,new_flight_number,expected_len,expected_delay,expected_number", [
    ("FRA", [], 15, "LH123", 1, 15, "LH123"),
    ("FRA", [{'destination':'FRA','predicted_delay':10,'flight_number':'OLD','destination_coords':[0,0],'source_coords':[0,0]}],
     20, "LH124", 1, 20, "LH124"),
    ("AMS", [], 5, "LH124", 1, 5, "LH124"),
    ("CDG", [{'destination':'FRA','predicted_delay':10,'flight_number':'OLD','destination_coords':[0,0],'source_coords':[0,0]}],
     12, "AF456", 2, 12, "AF456"),
])
def test_add_flight_for_visualization(destination_iata, prev_flights, new_delay, new_flight_number,
                                      expected_len, expected_delay, expected_number):
    """
    Check if the data is added or replaced correctly in add_flight_for_visualization.
    """
    result = services.add_flight_for_visualization(destination_iata, new_delay, new_flight_number, prev_flights)
    assert len(result) == expected_len
    assert result[-1]['predicted_delay'] == expected_delay
    assert result[-1]['flight_number'] == expected_number
