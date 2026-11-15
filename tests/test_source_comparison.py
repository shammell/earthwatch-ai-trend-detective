import pandas as pd

from source_comparison import compare_temperature_sources
from trend_models import SourceMetadata


def _frame(slope):
    dates = pd.date_range("2020-01-01", periods=730, freq="D")
    values = [20 + slope * i for i in range(730)]
    return pd.DataFrame({
        "Temp_Avg": values, "Temp_Max": [v + 5 for v in values],
        "Temp_Min": [v - 5 for v in values], "Rainfall_mm": [1.0] * 730,
        "Humidity_pct": [50.0] * 730, "Solar_kWh_m2": [1.0] * 730,
    }, index=dates)


def _source(provider):
    return SourceMetadata(provider, "https://example.test", "temperature", "mixed",
                          "daily", "2020-01-01", "2020-03-01", provider)


def test_sources_agree_without_merging():
    result = compare_temperature_sources(_frame(0.1), _frame(0.05), _source("NASA"), _source("NOAA"))
    assert result.status == "agreement"
    assert result.overlap_count == 730
    assert result.nasa_source.provider == "NASA"


def test_sources_disagree():
    result = compare_temperature_sources(_frame(0.1), _frame(-0.05), _source("NASA"), _source("NOAA"))
    assert result.status == "disagreement"


def test_insufficient_overlap():
    noaa = _frame(0.1)
    noaa.index = pd.date_range("2022-01-01", periods=730, freq="D")
    result = compare_temperature_sources(_frame(0.1), noaa, _source("NASA"), _source("NOAA"))
    assert result.status == "insufficient_overlap"
