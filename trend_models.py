"""Typed models shared by source adapters and climate analysis reports."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Union


class Significance(Enum):
    """Categorical interpretation of statistical trend evidence."""

    SIGNIFICANT = "significant"
    NOT_SIGNIFICANT = "not_significant"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass
class QualitySummary:
    """Summary of the observations included in an analysis."""

    valid: bool
    coverage_fraction: float
    total_count: int = 0
    valid_count: int = 0
    missing_count: int = 0
    flags: list[str] = field(default_factory=list)


@dataclass
class SourceMetadata:
    """Provenance and processing details for a normalized source series."""

    provider: str
    endpoint: str
    variable: str
    units: str
    temporal_resolution: str
    coverage_start: str
    coverage_end: str
    processing: str


@dataclass
class TrendResult:
    """A trend estimate and the evidence supporting its interpretation."""

    slope_per_decade: float
    lower_bound: float
    upper_bound: float
    p_value: float
    sample_count: int
    significance: Significance


@dataclass
class AnalysisWarning:
    """A limitation or caveat that should be shown with analysis results."""

    message: str
    code: str = "general"


@dataclass
class AnalysisReport:
    """Structured, serializable payload for a climate analysis report."""

    quality: QualitySummary
    trends: dict[str, TrendResult] = field(default_factory=dict)
    warnings: list[Union[str, AnalysisWarning]] = field(default_factory=list)
    location: Optional[str] = None
    source: Optional[SourceMetadata] = None
