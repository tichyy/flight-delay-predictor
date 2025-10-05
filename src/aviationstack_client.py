import os
import json
import time
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

AVIATIONSTACK_BASE_URL = "https://api.aviationstack.com/v1/"

def post_query(endpoint, params={}):
    params['access_key'] = os.getenv("AVIATIONSTACK_API_KEY")

    url = f"{AVIATIONSTACK_BASE_URL}{endpoint}"
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        response_json = response.json()
        return response_json
    except requests.exceptions.HTTPError as e:
        st.error(f"Too many requests. Try again in 10 minutes.")
        return None
    except requests.exceptions as e:
        st.error(f"API request failed: {e}")
        return None
    
@st.cache_data(ttl=600) # Cache for 10 minutes
def fetch_query(endpoint, params={}):
    return post_query(endpoint, params)