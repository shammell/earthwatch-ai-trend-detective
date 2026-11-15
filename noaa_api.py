"""Secure NOAA Climate Data Online station adapter."""

from dataclasses import dataclass
import os
from typing import Any

import pandas as pd
import requests

from trend_models import SourceMetadata

NOAA_ENDPOINT = "https://www.ncei.noaa.gov/cdo-web/api/v2"
NOAA_TOKEN_ENV = "NOAA_CDO_TOKEN"


class MissingNOAATokenError(RuntimeError):
    """Raised when NOAA access is requested without a configured token."""


class NOAAAPIError(RuntimeError):
    """Raised for NOAA transport or response errors."""


class NoStationsFoundError(ValueError):
    """Raised when a station search returns no stations."""


@dataclass(frozen=True)
class NOAAStation:
    id: str
    name: str
    latitude: float | None = None
    longitude: float | None = None


def _token() -> str:
    token = os.environ.get(NOAA_TOKEN_ENV, "").strip()
    if not token:
        raise MissingNOAATokenError(
            "NOAA comparison is unavailable: set NOAA_CDO_TOKEN in the environment."
        )
    return token


def _get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        response = requests.get(
            f"{NOAA_ENDPOINT}{path}",
            params=params,
            headers={"token": _token()},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
    except MissingNOAATokenError:
        raise
    except (requests.RequestException, ValueError) as exc:
        raise NOAAAPIError(f"NOAA request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise NOAAAPIError("NOAA returned an invalid response")
    return payload


def search_stations(
    latitude: float, longitude: float, start_date: str, end_date: str,
    radius: float = 1.0, limit: int = 10,
) -> list[NOAAStation]:
    """Find GHCND stations near a coordinate, preserving NOAA identity."""
    extent = f"{latitude-radius},{longitude-radius},{latitude+radius},{longitude+radius}"
    payload = _get("/stations", {
        "datasetid": "GHCND", "extent": extent, "startdate": start_date,
        "enddate": end_date, "limit": limit, "sortfield": "name",
    })
    stations = [
        NOAAStation(str(item["id"]), str(item.get("name", item["id"])),
                    item.get("latitude"), item.get("longitude"))
        for item in payload.get("results", [])
        if item.get("id")
    ]
    if not stations:
        raise NoStationsFoundError("No NOAA GHCND stations were found for this location.")
    return stations


def fetch_noaa_observations(
    station: NOAAStation | str, start_date: str, end_date: str,
) -> tuple[pd.DataFrame, SourceMetadata]:
    """Fetch and normalize daily GHCND station observations."""
    station_id = station.id if isinstance(station, NOAAStation) else str(station)
    payload = _get("/data", {
        "datasetid": "GHCND", "stationid": station_id, "startdate": start_date,
        "enddate": end_date, "units": "metric", "limit": 1000,
        "datatypeid": "TAVG,TMAX,TMIN,PRCP",
    })
    rows = payload.get("results", [])
    if not rows:
        raise ValueError("No NOAA station observations were returned.")
    raw = pd.DataFrame(rows)
    raw["date"] = pd.to_datetime(raw["date"], errors="coerce").dt.normalize()
    values = raw.pivot_table(index="date", columns="datatype", values="value", aggfunc="first")
    values = values.rename(columns={"TAVG": "Temp_Avg", "TMAX": "Temp_Max",
                                    "TMIN": "Temp_Min", "PRCP": "Rainfall_mm"})
    # A station payload can omit a datatype; retain the shared analysis contract.
    for column in ("Temp_Avg", "Temp_Max", "Temp_Min", "Rainfall_mm"):
        if column not in values:
            values[column] = pd.NA
    values["Humidity_pct"] = 50.0
    values["Solar_kWh_m2"] = 0.0
    values = values[["Temp_Avg", "Temp_Max", "Temp_Min", "Rainfall_mm",
                     "Humidity_pct", "Solar_kWh_m2"]].sort_index()
    values = values.replace(-999.0, pd.NA)
    if values.dropna(subset=["Temp_Avg", "Temp_Max", "Temp_Min"]).empty:
        raise ValueError("NOAA returned no usable temperature observations.")
    values.index.name = "Date"
    station_name = station.name if isinstance(station, NOAAStation) else station_id
    source = SourceMetadata(
        provider="NOAA Climate Data Online",
        endpoint=f"{NOAA_ENDPOINT}/data",
        variable="GHCND TAVG,TMAX,TMIN,PRCP",
        units="°C and mm",
        temporal_resolution="daily",
        coverage_start=start_date,
        coverage_end=end_date,
        processing=f"NOAA station observation; station={station_id} ({station_name})",
    )
    return values, source
