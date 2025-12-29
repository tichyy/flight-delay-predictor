"""
API client interface for the AviationStack flight data service.
Handles the HTTP communication with the AviationStack API.
"""
import requests
import streamlit as st

AVIATIONSTACK_BASE_URL = "https://api.aviationstack.com/v1/"

API_KEY_ARRIVAL = st.secrets.get('AVIATIONSTACK_2_API_KEY')
API_KEY_DEPARTURE = st.secrets.get('AVIATIONSTACK_API_KEY')


def post_query(endpoint: str, params: dict = None) -> dict:
    """
    Executes a GET request to the AviationStack API.
    
    :param endpoint: API endpoint to query ('timetable', 'flights', ...).
    :type endpoint: str
    :param params: Optional query parameters ('date', 'type', ...).
    :type params: dict
    :return: JSON response from the API.
    :rtype: dict
    """
    if params is None:
        params = {}

    if 'type' in params and params['type'] == 'arrival':
        api_key = API_KEY_ARRIVAL
    else:
        api_key = API_KEY_DEPARTURE

    if not api_key:
        raise ValueError('AVIATIONSTACK_API_KEY variable is missing!')

    params['access_key'] = api_key
    url = f"{AVIATIONSTACK_BASE_URL}{endpoint}"

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    return data


@st.cache_data(ttl=300) # Cache for 5 minutes
def fetch_query(endpoint: str, params: dict = None) -> dict:
    """
    Wrapper for 'post_query'. Caches results for 5 minutes. 
    Function prevents unwanted caching of invalid states by raising a ValueError.
    
    :param endpoint: API endpoint to query.
    :type endpoint: str
    :param params: Optional query parameters.
    :type params: dict
    :return: JSON response data.
    :rtype: dict
    """
    res = post_query(endpoint, params)
    if res is None:
        raise ValueError('Empty API response - prevented caching')
    return res
