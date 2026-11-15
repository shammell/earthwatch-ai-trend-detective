import pytest
import requests

from nasa_api import fetch_nasa_climate_data


class FakeResponse:
    def __init__(self, payload, status_error=None):
        self.payload = payload
        self.status_error = status_error

    def raise_for_status(self):
        if self.status_error is not None:
            raise self.status_error

    def json(self):
        return self.payload


def test_fetch_normalizes_power_payload(power_payload, monkeypatch):
    response = FakeResponse(power_payload)
    monkeypatch.setattr("nasa_api.requests.get", lambda *args, **kwargs: response)

    frame, source = fetch_nasa_climate_data(
        24.7475, 67.9235, "20200101", "20201231"
    )

    assert frame.index.name == "Date"
    assert {"Temp_Avg", "Temp_Max", "Temp_Min", "Rainfall_mm"} <= set(frame.columns)
    assert frame.dtypes["Temp_Avg"].kind == "f"
    assert len(frame) == 1
    assert source.provider == "NASA POWER"
    assert source.coverage_start == "20200101"
    assert source.coverage_end == "20201231"


def test_fetch_surfaces_http_failures(monkeypatch):
    error = requests.HTTPError("NASA unavailable")
    response = FakeResponse({}, status_error=error)
    monkeypatch.setattr("nasa_api.requests.get", lambda *args, **kwargs: response)

    with pytest.raises(requests.HTTPError, match="NASA unavailable"):
        fetch_nasa_climate_data(24.7475, 67.9235, "20200101", "20201231")


def test_fetch_rejects_payload_without_valid_rows(monkeypatch):
    payload = {
        "properties": {
            "parameter": {
                "T2M": {"20200101": -999.0},
                "T2M_MAX": {"20200101": 25.0},
                "T2M_MIN": {"20200101": 15.0},
                "PRECTOTCORR": {"20200101": 1.2},
                "RH2M": {"20200101": 60.0},
                "ALLSKY_SFC_SW_DWN": {"20200101": 4.5},
            }
        }
    }
    response = FakeResponse(payload)
    monkeypatch.setattr("nasa_api.requests.get", lambda *args, **kwargs: response)

    with pytest.raises(ValueError, match="No valid NASA POWER observations"):
        fetch_nasa_climate_data(24.7475, 67.9235, "20200101", "20201231")


