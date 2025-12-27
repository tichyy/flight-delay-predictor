# BI-PYT Semestral Work - Flight Delay Prediction app with Streamlit

This project is a Streamlit-based web application designed to display todays airport departure boards and predict flight delays with ML.

Departure Board: View real-time or scheduled flights for specific airports. (only PRG airport for now.)

Delay Prediction: Predict the expected delay (in minutes) for a specific flight number and date. (Only today's flights from PRG airport!)

Visualization: Render flight paths on an interactive map.

## Project Structure

```
flight-delay-predictor/
├── app/
│   └── main.py                 # Main Streamlit application entry point
├── src/
│   └── flight_delay/
│       ├── api/
│       │   └── aviationstack_client.py  # API client for flight data
│       ├── utils/
│       │   └── dicts.py        # Utility functions and dictionaries
│       ├── data_preprocessing.py        # Data preprocessing functions
│       ├── services.py         # Logic and prediction services
│       └── ui.py               # UI rendering
├── data/
│   ├── raw/                    # Raw flight and weather data
│   │   ├── arrivals_250101_250430.csv
│   │   ├── departures_250101_250430.csv
│   │   └── weather_250101_250430.csv
│   └── processed/              # Processed data and configurations
│       ├── categories.json
│       ├── data_exploration.csv
│       └── fill_values.json
├── models/
│   └── flight_delay_xgb.joblib # Trained XGBoost model
├── notebooks/
│   ├── 01_data_preprocessing.ipynb      # Preprocessing of the raw datasets and XGBoost training.
│   └── 02_data_exploration.ipynb        # Very simple EDA
├── tests/                      # Unit tests
│   ├── test_aviationstack_client.py
│   ├── test_services.py
│   └── test_ui.py
├── pyproject.toml              # Project configuration
└── uv.lock                     # Dependency lock file
```

## Installation

### Prerequisites

- Python 3.10+
- UV package manager (recommended) or pip

Recommended step:
```bash
pip install uv
```

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd flight-delay-predictor
```

2. Install dependencies into a virtual environment:
```bash
uv sync  

# or all this:

python3 -m venv .venv 
source .venv/bin/activate     # Linux/MacOS
# .venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt
```

3. Create a .env file in the flight-delay-predictor directory.
You need to sign up for a free account at https://aviationstack.com/ and paste the API key into the .env file. Both keys must be filled.
```
AVIATIONSTACK_API_KEY=''
AVIATIONSTACK_API_2_KEY='' # Can be the same key or a 2nd account (recommended).
```

4. Run the Streamlit application in the virtual environment:

```bash
uv run streamlit run app/main.py
# or
# with the virtual environment active:
streamlit run app/main.py
```

The application will open in your default web browser at `http://localhost:8501`.

### Using the App

1. **Select Airport**: Choose an airport from the dropdown menu (limited to PRG only)
2. **View Departure Board**: See the current flight schedule
3. **Predict Delay**: 
   - Enter a flight number (limited to flight departuring from PRG Airport today)
   - Select a departure date (limited to TODAY)
   - Click "Predict Delay"
4. **View Results**: See the predicted delay time and flight visualization on the map

## Development

### Running Tests

Execute the tests using pytest:

```bash
pytest tests/
```

### Project Configuration

The project uses `pyproject.toml` for configuration and dependency management.

## Data

The model is trained on historical flight data from January to April 2025, including:
- Departure schedules
- Arrival schedules
- Weather conditions

Data preprocessing and exploration notebooks are in the `notebooks/` directory.

## API Integration

The application integrates with the AviationStack API and Open-Meteo API to fetch real-time flight information.
