import requests
import pandas as pd
import streamlit as st

from trend_models import SourceMetadata


NASA_POWER_ENDPOINT = "https://power.larc.nasa.gov/api/temporal/daily/point"
NASA_PARAMETERS = (
    "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,RH2M,ALLSKY_SFC_SW_DWN"
)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_nasa_climate_data(
    lat: float, lon: float, start_date: str, end_date: str
) -> tuple[pd.DataFrame, SourceMetadata]:
    """Fetch daily NASA POWER records and return normalized data with provenance."""
    params = {
        "parameters": NASA_PARAMETERS,
        "community": "RE",
        "longitude": lon,
        "latitude": lat,
        "start": start_date,
        "end": end_date,
        "format": "JSON",
    }
    response = requests.get(NASA_POWER_ENDPOINT, params=params, timeout=30)
    response.raise_for_status()
    raw = response.json()["properties"]["parameter"]

    df = pd.DataFrame(raw)
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df = df.replace(-999.0, pd.NA).dropna()
    if df.empty:
        raise ValueError("No valid NASA POWER observations were returned")
    df = df.astype(float)
    df.index.name = "Date"

    df = df.rename(
        columns={
            "T2M": "Temp_Avg",
            "T2M_MAX": "Temp_Max",
            "T2M_MIN": "Temp_Min",
            "PRECTOTCORR": "Rainfall_mm",
            "RH2M": "Humidity_pct",
            "ALLSKY_SFC_SW_DWN": "Solar_kWh_m2",
        }
    )
    source = SourceMetadata(
        provider="NASA POWER",
        endpoint=NASA_POWER_ENDPOINT,
        variable=NASA_PARAMETERS,
        units="mixed meteorological and solar units",
        temporal_resolution="daily",
        coverage_start=start_date,
        coverage_end=end_date,
        processing=(
            f"NASA POWER reanalysis; latitude={lat}; longitude={lon}; "
            f"parameters={NASA_PARAMETERS}"
        ),
    )
    return df, source
