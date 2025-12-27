"""
Tests for src/flight_delay/api/aviationstack_client.py
Just quick verification of error handling.
"""
import sys
from types import SimpleNamespace
import requests
import pytest

# Simple mock for Streamlit, we just need to mock cache_data
sys.modules["streamlit"] = SimpleNamespace(
    cache_data=lambda ttl=None: (lambda f: f)
)

# Import after mocking
from flight_delay.api.aviationstack_client import post_query, fetch_query

class FakeResponse:
    """
    Mock API response class
    """
    def __init__(self, data=None, raise_error=False):
        """
        Init method
        """
        self._data = data or {}
        self._raise_error = raise_error

    def raise_for_status(self):
        """
        Mock raise for status
        """
        if self._raise_error:
            raise requests.HTTPError("HTTP error")

    def json(self):
        """
        Mock response json
        """
        return self._data

def test_post_query_missing_api_key(monkeypatch):
    """
    Check if a ValueError is raised when no API key found.
    """
    monkeypatch.delenv("AVIATIONSTACK_API_KEY", raising=False)
    monkeypatch.delenv("AVIATIONSTACK_2_API_KEY", raising=False)

    with pytest.raises(ValueError):
        post_query("timetable")


def test_post_query_http_error(monkeypatch):
    """
    Check if HTTP errors from the requests library are raised.
    """
    monkeypatch.setenv("AVIATIONSTACK_API_KEY", "KEY")
    monkeypatch.setattr(
        requests,
        "get",
        lambda *a, **k: FakeResponse(raise_error=True),
    )

    with pytest.raises(requests.HTTPError):
        post_query("timetable")


def test_fetch_query_raises_on_none(monkeypatch):
    """
    Check if fetch_query raises an error when post_query returns None.
    This prevents invalid results from being cached.
    """
    monkeypatch.setattr("flight_delay.api.aviationstack_client.post_query", lambda *a, **k: None)

    with pytest.raises(ValueError):
        fetch_query("timetable")
