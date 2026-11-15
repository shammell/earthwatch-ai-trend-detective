import pytest
import pandas as pd


@pytest.fixture(autouse=True)
def clear_streamlit_cache():
    from nasa_api import fetch_nasa_climate_data

    fetch_nasa_climate_data.clear()
    yield
    fetch_nasa_climate_data.clear()


@pytest.fixture
def power_payload():
    return {
        "properties": {
            "parameter": {
                "T2M": {"20200101": 20.0, "20200102": -999.0},
                "T2M_MAX": {"20200101": 25.0, "20200102": 26.0},
                "T2M_MIN": {"20200101": 15.0, "20200102": 16.0},
                "PRECTOTCORR": {"20200101": 1.2, "20200102": 0.0},
                "RH2M": {"20200101": 60.0, "20200102": 65.0},
                "ALLSKY_SFC_SW_DWN": {"20200101": 4.5, "20200102": 4.7},
            }
        }
    }


def _analysis_frame(index, temperatures, rainfall=None):
    rainfall = rainfall or [1.0] * len(index)
    return pd.DataFrame(
        {
            "Temp_Avg": temperatures,
            "Temp_Max": [value + 4 for value in temperatures],
            "Temp_Min": [value - 4 for value in temperatures],
            "Rainfall_mm": rainfall,
            "Humidity_pct": [60.0] * len(index),
            "Solar_kWh_m2": [5.0] * len(index),
        },
        index=index,
    )


@pytest.fixture
def monthly_trend():
    index = pd.date_range("2020-01-31", periods=36, freq="ME")
    return _analysis_frame(index, [20.0 + month * 0.2 for month in range(36)])


@pytest.fixture
def short_series():
    index = pd.date_range("2024-01-01", periods=3, freq="D")
    return _analysis_frame(index, [25.0, 25.2, 25.1])


@pytest.fixture
def rainfall_with_event():
    index = pd.date_range("2020-01-01", periods=12, freq="ME")
    rainfall = [2.0] * 11 + [100.0]
    return _analysis_frame(index, [25.0] * 12, rainfall)


@pytest.fixture
def monthly_with_missing_data():
    index = pd.to_datetime(["2020-01-31", "2020-03-31", "2020-04-30", "2020-06-30"])
    return _analysis_frame(index, [20.0, 20.5, 20.7, 21.0])
