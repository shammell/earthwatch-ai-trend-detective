import pandas as pd
import pytest

import noaa_api
from noaa_api import (
    MissingNOAATokenError,
    NOAAStation,
    NoStationsFoundError,
    fetch_noaa_observations,
    search_stations,
)


class Response:
    def __init__(self, payload, status=200):
        self.payload, self.status = payload, status

    def raise_for_status(self):
        if self.status >= 400:
            import requests
            raise requests.HTTPError("bad response")

    def json(self):
        return self.payload


def test_missing_token_is_clear(monkeypatch):
    monkeypatch.delenv("NOAA_CDO_TOKEN", raising=False)
    with pytest.raises(MissingNOAATokenError, match="NOAA_CDO_TOKEN"):
        search_stations(24.8, 67.0, "2020-01-01", "2020-01-31")


def test_station_metadata_and_normalization(monkeypatch):
    monkeypatch.setenv("NOAA_CDO_TOKEN", "test-token")
    payloads = [
        {"results": [{"id": "GHCND:PKM00041780", "name": "KARACHI", "latitude": 24.9,
                      "longitude": 67.1}]},
        {"results": [
            {"date": "2020-01-01T00:00:00", "datatype": "TAVG", "value": 20.0},
            {"date": "2020-01-01T00:00:00", "datatype": "TMAX", "value": 25.0},
            {"date": "2020-01-01T00:00:00", "datatype": "TMIN", "value": 15.0},
            {"date": "2020-01-01T00:00:00", "datatype": "PRCP", "value": 2.0},
        ]},
    ]
    monkeypatch.setattr(noaa_api.requests, "get", lambda *args, **kwargs: Response(payloads.pop(0)))
    stations = search_stations(24.8, 67.0, "2020-01-01", "2020-01-31")
    frame, source = fetch_noaa_observations(stations[0], "2020-01-01", "2020-01-31")
    assert stations[0].id == "GHCND:PKM00041780"
    assert frame.loc[pd.Timestamp("2020-01-01"), "Temp_Avg"] == 20
    assert source.processing.startswith("NOAA station observation")


def test_empty_station_results_are_explicit(monkeypatch):
    monkeypatch.setenv("NOAA_CDO_TOKEN", "test-token")
    monkeypatch.setattr(noaa_api.requests, "get", lambda *args, **kwargs: Response({"results": []}))
    with pytest.raises(NoStationsFoundError):
        search_stations(0, 0, "2020-01-01", "2020-01-31")
