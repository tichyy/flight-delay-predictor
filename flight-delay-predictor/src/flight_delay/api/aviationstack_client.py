import os
import json
import time
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv(override=True)

AVIATIONSTACK_BASE_URL = "https://api.aviationstack.com/v1/"

def post_query(endpoint, params=None):
    if params is None:
        params = {}

    # uncomment on 1.1.2026
    # if 'type' in params and params['type'] == 'arrival':
    #     api_key = os.getenv("AVIATIONSTACK_2_API_KEY")
    # else:
    #     api_key = os.getenv("AVIATIONSTACK_API_KEY")

    api_key = os.getenv("AVIATIONSTACK_API_KEY")

    if not api_key:
        raise ValueError("AVIATIONSTACK_API_KEY variable is missing!")

    params['access_key'] = api_key
    url = f"{AVIATIONSTACK_BASE_URL}{endpoint}"

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    return data
    
@st.cache_data(ttl=300) # Cache for 5 minutes
def fetch_query(endpoint, params: dict):
    res = post_query(endpoint, params)
    if res is None:
        raise ValueError("Empty API response - prevented caching")
    return res