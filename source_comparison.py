"""Compare independently analyzed NASA and NOAA evidence."""

from dataclasses import dataclass
import pandas as pd

from analyzer import analyze_climate_data
from trend_models import AnalysisReport, SourceMetadata, TrendResult


@dataclass(frozen=True)
class SourceComparison:
    nasa_source: SourceMetadata
    noaa_source: SourceMetadata
    nasa_trend: TrendResult
    noaa_trend: TrendResult
    overlap_count: int
    status: str
    message: str


def compare_temperature_sources(
    nasa: pd.DataFrame, noaa: pd.DataFrame,
    nasa_source: SourceMetadata, noaa_source: SourceMetadata,
    location_name: str = "selected location", min_overlap: int = 30,
) -> SourceComparison:
    """Analyze each source separately, then compare temperature trend direction."""
    overlap = nasa.index.intersection(noaa.index)
    nasa_report: dict = analyze_climate_data(nasa, location_name, nasa_source)
    noaa_report: dict = analyze_climate_data(noaa, location_name, noaa_source)
    nasa_trend = nasa_report["trends"]["Temp_Avg"]
    noaa_trend = noaa_report["trends"]["Temp_Avg"]
    if len(overlap) < min_overlap:
        status, message = "insufficient_overlap", "Sources do not have enough overlapping daily coverage."
    elif nasa_trend.significance.value == "insufficient_evidence" or noaa_trend.significance.value == "insufficient_evidence":
        status, message = "insufficient_evidence", "One source has insufficient trend evidence."
    elif nasa_trend.slope_per_decade * noaa_trend.slope_per_decade >= 0:
        status, message = "agreement", "NASA and NOAA temperature trends have the same direction."
    else:
        status, message = "disagreement", "NASA and NOAA temperature trends have different directions."
    return SourceComparison(nasa_source, noaa_source, nasa_trend, noaa_trend,
                            len(overlap), status, message)
