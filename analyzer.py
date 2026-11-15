"""Validated climate trend calculations and legacy dashboard indicators."""

from math import erfc, sqrt

import numpy as np
import pandas as pd

from trend_models import QualitySummary, Significance, SourceMetadata, TrendResult


REQUIRED_COLUMNS = (
    "Temp_Avg",
    "Temp_Max",
    "Temp_Min",
    "Rainfall_mm",
    "Humidity_pct",
    "Solar_kWh_m2",
)


def calculate_heat_index(temp_c: pd.Series, rh: pd.Series) -> pd.Series:
    """Approximate feels-like heat index in °C using Rothfusz regression."""
    t_f = temp_c * 9 / 5 + 32
    hi_f = (
        -42.379
        + 2.04901523 * t_f
        + 10.14333127 * rh
        - 0.22475541 * t_f * rh
        - 0.00683783 * (t_f**2)
        - 0.05481717 * (rh**2)
        + 0.00122874 * (t_f**2) * rh
        + 0.00085282 * t_f * (rh**2)
        - 0.00000199 * (t_f**2) * (rh**2)
    )
    hi_c = (hi_f - 32) * 5 / 9
    return np.where((temp_c >= 27.0) & (rh >= 40.0), hi_c, temp_c)


def validate_observations(df: pd.DataFrame) -> QualitySummary:
    """Validate the normalized observation contract and summarize coverage."""
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("Observations must use a DatetimeIndex")
    if not df.index.is_monotonic_increasing or not df.index.is_unique:
        raise ValueError("Observation dates must be sorted and unique")

    numeric = df.loc[:, REQUIRED_COLUMNS].apply(pd.to_numeric, errors="coerce")
    valid_rows = np.isfinite(numeric.to_numpy()).all(axis=1)
    total_count = len(df)
    valid_count = int(valid_rows.sum())
    coverage = valid_count / total_count if total_count else 0.0
    flags = [] if coverage >= 0.8 else ["coverage_below_minimum"]
    if valid_count < total_count:
        flags.append("missing_or_non_finite_values")
    return QualitySummary(
        valid=bool(total_count and coverage >= 0.8),
        coverage_fraction=coverage,
        total_count=total_count,
        valid_count=valid_count,
        missing_count=total_count - valid_count,
        flags=flags,
    )


def prepare_monthly_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate observations while retaining empty months for honest coverage."""
    numeric = df.loc[:, REQUIRED_COLUMNS].apply(pd.to_numeric, errors="coerce")
    monthly = numeric.resample("ME").agg(
        {
            "Temp_Avg": "mean",
            "Temp_Max": "max",
            "Temp_Min": "min",
            "Rainfall_mm": lambda values: values.sum(min_count=1),
            "Humidity_pct": "mean",
            "Solar_kWh_m2": "mean",
        }
    )
    return monthly


def _mann_kendall_p_value(values: np.ndarray) -> float:
    n = len(values)
    signs = np.sign(values[None, :] - values[:, None])
    s = float(np.triu(signs, 1).sum())
    _, counts = np.unique(values, return_counts=True)
    tie_term = float(np.sum(counts * (counts - 1) * (2 * counts + 5)))
    variance = (n * (n - 1) * (2 * n + 5) - tie_term) / 18
    if variance <= 0 or s == 0:
        return 1.0
    z = (s - np.sign(s)) / sqrt(variance)
    return float(erfc(abs(z) / sqrt(2)))


def calculate_trend(series: pd.Series, periods_per_year: float) -> TrendResult:
    """Calculate a Theil–Sen rate and Mann–Kendall evidence for a series."""
    clean = series.dropna().astype(float)
    n = len(clean)
    if n < 12:
        return TrendResult(0.0, 0.0, 0.0, 1.0, n, Significance.INSUFFICIENT_EVIDENCE)

    if isinstance(clean.index, pd.DatetimeIndex):
        x = np.asarray(
            (clean.index - clean.index[0]).total_seconds() / (365.25 * 86400),
            dtype=float,
        )
    else:
        x = np.arange(n, dtype=float) / periods_per_year
    values = clean.to_numpy()
    denominator = x[None, :] - x[:, None]
    numerator = values[None, :] - values[:, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        slopes = (numerator / denominator)[np.triu_indices(n, 1)]
    slopes = slopes[np.isfinite(slopes)]
    if not len(slopes):
        return TrendResult(0.0, 0.0, 0.0, 1.0, n, Significance.INSUFFICIENT_EVIDENCE)
    slope = float(np.median(slopes) * 10)
    lower, upper = (float(value * 10) for value in np.quantile(slopes, [0.025, 0.975]))
    p_value = _mann_kendall_p_value(values)
    significance = Significance.SIGNIFICANT if p_value < 0.05 else Significance.NOT_SIGNIFICANT
    return TrendResult(slope, lower, upper, p_value, n, significance)


def classify_events(df: pd.DataFrame) -> pd.DataFrame:
    """Screen daily observations for unusual heat and precipitation events."""
    temp = pd.to_numeric(df["Temp_Max"], errors="coerce")
    rain = pd.to_numeric(df["Rainfall_mm"], errors="coerce")
    temp_std = temp.std()
    rain_std = rain.std()
    heat_threshold = temp.mean() + 2 * (0.0 if pd.isna(temp_std) else temp_std)
    rain_threshold = max(15.0, rain.mean() + 2 * (0.0 if pd.isna(rain_std) else rain_std))
    heat = df[temp > heat_threshold].copy()
    heat["Event_Type"] = "Extreme Heat Spike"
    heavy_rain = df[rain > rain_threshold].copy()
    heavy_rain["Event_Type"] = "Heavy Precipitation"
    return pd.concat([heat, heavy_rain]).sort_index(ascending=False)


def analyze_climate_data(
    df: pd.DataFrame, location_name: str, source: SourceMetadata | None = None
) -> dict:
    """Return robust trends alongside the existing dashboard analysis fields."""
    quality = validate_observations(df)
    numeric = df.loc[:, REQUIRED_COLUMNS].apply(pd.to_numeric, errors="coerce")
    clean = numeric[np.isfinite(numeric).all(axis=1)].copy()
    if clean.empty:
        raise ValueError("No valid observations remain after validation")
    clean["Feels_Like_Max"] = calculate_heat_index(clean["Temp_Max"], clean["Humidity_pct"])

    monthly_frame = prepare_monthly_analysis(clean)
    monthly = monthly_frame.copy()
    monthly.index = monthly.index.strftime("%Y-%m")
    if quality.valid:
        trends = {
            column: calculate_trend(monthly_frame[column], 12.0)
            for column in ("Temp_Avg", "Rainfall_mm")
        }
    else:
        trends = {
            column: calculate_trend(pd.Series(dtype=float), 12.0)
            for column in ("Temp_Avg", "Rainfall_mm")
        }
    anomalies = classify_events(clean)
    heat_anomalies = anomalies[anomalies["Event_Type"] == "Extreme Heat Spike"]
    rain_anomalies = anomalies[anomalies["Event_Type"] == "Heavy Precipitation"]
    temp_threshold = clean["Temp_Max"].mean() + 2 * clean["Temp_Max"].std()
    rain_threshold = max(15.0, clean["Rainfall_mm"].mean() + 2 * clean["Rainfall_mm"].std())
    temp_slope_year = trends["Temp_Avg"].slope_per_decade / 10
    recent_30 = clean.tail(30)
    anomaly_rate = len(anomalies) / len(clean) * 100
    if not quality.valid:
        stress_level, stress_color = "INSUFFICIENT EVIDENCE", "⚪"
    elif anomaly_rate > 4.5 or temp_slope_year > 0.15:
        stress_level, stress_color = "ELEVATED", "🔴"
    elif anomaly_rate > 2.5 or temp_slope_year > 0.05:
        stress_level, stress_color = "MODERATE", "🟡"
    else:
        stress_level, stress_color = "STABLE", "🟢"
    trend_word = "insufficient evidence" if not quality.valid else ("warming" if temp_slope_year > 0.05 else (
        "cooling" if temp_slope_year < -0.05 else "thermally stable"
    ))
    wettest_month = monthly["Rainfall_mm"].idxmax()
    wettest_value = monthly["Rainfall_mm"].max()
    warnings = ["Event classifications are screening indicators, not proof of a long-term trend."]
    if not quality.valid:
        warnings.append("Insufficient observation coverage: trend evidence is not reported.")
    insights = [
        {"title": "Temperature Trajectory", "body": f"{location_name} exhibits a **{trend_word}** rate of **{temp_slope_year:+.2f}°C/year**. Peak recorded temperature hit **{clean['Temp_Max'].max():.1f}°C** (feels like **{clean['Feels_Like_Max'].max():.1f}°C** with humidity)."},
        {"title": "Rainfall & Monsoon Concentration", "body": f"Cumulative precipitation reached **{clean['Rainfall_mm'].sum():.1f} mm** over **{len(clean[clean['Rainfall_mm'] > 1.0])} rainy days**. The wettest month was **{wettest_month}** with **{wettest_value:.1f} mm**."},
        {"title": "Unusual Weather & Solar Profile", "body": f"Detected **{len(heat_anomalies)} heat spikes** (>{temp_threshold:.1f}°C) and **{len(rain_anomalies)} heavy rain surges** (>{rain_threshold:.1f} mm/day). Mean solar irradiance is **{clean['Solar_kWh_m2'].mean():.2f} kWh/m²/day**."},
    ]
    return {
        "df": clean,
        "source": source,
        "quality": quality,
        "evidence_valid": quality.valid,
        "trends": trends,
        "warnings": warnings,
        "monthly": monthly,
        "avg_temp": clean["Temp_Avg"].mean(),
        "temp_delta_30d": recent_30["Temp_Avg"].mean() - clean["Temp_Avg"].mean(),
        "max_temp": clean["Temp_Max"].max(),
        "max_feels_like": clean["Feels_Like_Max"].max(),
        "total_rain": clean["Rainfall_mm"].sum(),
        "avg_humidity": clean["Humidity_pct"].mean(),
        "humidity_delta_30d": recent_30["Humidity_pct"].mean() - clean["Humidity_pct"].mean(),
        "anomaly_count": len(anomalies),
        "all_anomalies": anomalies,
        "event_summary": {"heat_spike_count": len(heat_anomalies), "heavy_rain_count": len(rain_anomalies)},
        "stress_level": stress_level,
        "stress_color": stress_color,
        "insights": insights,
    }
