import pytest


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
