import json

from trend_models import (
    AnalysisReport,
    QualitySummary,
    Significance,
    SourceMetadata,
    TrendResult,
)


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
