import json

import pandas as pd
import pytest

from analyzer import analyze_climate_data
from analyzer import (
    calculate_trend,
    classify_events,
    prepare_monthly_analysis,
    validate_observations,
)
from trend_models import (
    AnalysisReport,
    QualitySummary,
    Significance,
    SourceMetadata,
    TrendResult,
)


def test_analysis_preserves_source_metadata():
    frame = pd.DataFrame(
        {
            "Temp_Avg": [28.0, 29.0],
            "Temp_Max": [32.0, 33.0],
            "Temp_Min": [24.0, 25.0],
            "Rainfall_mm": [0.0, 1.0],
            "Humidity_pct": [60.0, 61.0],
            "Solar_kWh_m2": [5.0, 5.1],
        },
        index=pd.date_range("2020-01-01", periods=2, freq="D"),
    )
    source = SourceMetadata(
        provider="NASA POWER",
        endpoint="https://power.larc.nasa.gov/api/temporal/daily/point",
        variable="T2M",
        units="degC",
        temporal_resolution="daily",
        coverage_start="20200101",
        coverage_end="20200102",
        processing="reanalysis",
    )

    result = analyze_climate_data(frame, "Thatta", source)

    assert result["source"] is source


def test_source_metadata_preserves_provenance():
    source = SourceMetadata(
        provider="NASA POWER",
        endpoint="https://power.larc.nasa.gov/api/temporal/daily/point",
        variable="T2M",
        units="degC",
        temporal_resolution="daily",
        coverage_start="2020-01-01",
        coverage_end="2023-12-31",
        processing="reanalysis",
    )

    assert source.provider == "NASA POWER"
    assert source.processing == "reanalysis"


def test_trend_result_has_explicit_significance():
    result = TrendResult(
        slope_per_decade=0.25,
        lower_bound=0.10,
        upper_bound=0.40,
        p_value=0.01,
        sample_count=48,
        significance=Significance.SIGNIFICANT,
    )

    assert result.significance is Significance.SIGNIFICANT
    assert result.sample_count == 48


def test_analysis_report_serializes_nested_models_to_json():
    report = AnalysisReport(
        location="Thatta / Indus Delta",
        source=SourceMetadata(
            provider="NASA POWER",
            endpoint="https://power.larc.nasa.gov/api/temporal/daily/point",
            variable="T2M",
            units="degC",
            temporal_resolution="monthly",
            coverage_start="2020-01-01",
            coverage_end="2023-12-31",
            processing="reanalysis",
        ),
        quality=QualitySummary(valid=True, coverage_fraction=1.0),
        trends={
            "temperature": TrendResult(
                slope_per_decade=0.25,
                lower_bound=0.10,
                upper_bound=0.40,
                p_value=0.01,
                sample_count=48,
                significance=Significance.SIGNIFICANT,
            )
        },
    )

    payload = json.dumps(report.to_dict())

    assert '"significance": "significant"' in payload


def test_temperature_trend_is_reported_per_decade(monthly_trend):
    report = analyze_climate_data(monthly_trend, "Thatta / Indus Delta")
    result = report["trends"]["Temp_Avg"]

    assert result.slope_per_decade > 1.0
    assert result.sample_count == len(monthly_trend)
    assert result.significance.value in {"significant", "not_significant"}


def test_short_series_is_insufficient(short_series):
    report = analyze_climate_data(short_series, "Karachi, Pakistan")

    assert report["trends"]["Temp_Avg"].significance.value == "insufficient_evidence"


def test_rainfall_event_is_not_called_a_trend(rainfall_with_event):
    report = analyze_climate_data(rainfall_with_event, "Thatta / Indus Delta")

    assert report["event_summary"]["heavy_rain_count"] == 1
    assert report["trends"]["Rainfall_mm"].significance.value != "significant"


def test_monthly_preparation_keeps_missing_months_visible(monthly_with_missing_data):
    monthly = prepare_monthly_analysis(monthly_with_missing_data)

    missing_month = monthly.loc["2020-02-29", "Temp_Avg"]
    assert pd.isna(missing_month)


def test_validation_rejects_unsorted_duplicate_dates(monthly_trend):
    invalid = monthly_trend.iloc[[1, 0]].copy()
    invalid.index = [monthly_trend.index[0], monthly_trend.index[0]]

    with pytest.raises(ValueError, match="sorted and unique"):
        validate_observations(invalid)


def test_event_classifier_labels_heat_and_rain_events(rainfall_with_event):
    events = classify_events(rainfall_with_event)

    assert "Heavy Precipitation" in set(events["Event_Type"])


def test_sparse_observations_cannot_produce_usable_trends(monthly_trend):
    sparse = monthly_trend.copy()
    sparse.iloc[:10, :] = float("nan")

    report = analyze_climate_data(sparse, "Thatta / Indus Delta")

    assert report["quality"].valid is False
    assert report["evidence_valid"] is False
    assert all(
        trend.significance.value == "insufficient_evidence"
        for trend in report["trends"].values()
    )
    assert report["stress_level"] == "INSUFFICIENT EVIDENCE"
