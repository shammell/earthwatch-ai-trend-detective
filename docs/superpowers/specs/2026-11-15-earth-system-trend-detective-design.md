# Earth System Trend Detective: Indus Heat and Rainfall

## Status

Design approved in conversation; implementation has not started.

## Goal

Turn the existing EarthWatch AI Streamlit prototype into a guided, public-friendly
“data detective” experience for the Pakistan and Indus region. The first
investigation will answer:

> Is there a meaningful heat or rainfall change in this region, where is it
> occurring, how large is it, and is the evidence statistically significant?

The experience is intended for students and the general public, with NASA Space
Apps judges as an important demonstration audience.

## Scope

### In scope for the first version

- Pakistan and Indus-region locations, including Karachi/coast, Thatta/Indus
  Delta, Lahore, Islamabad, and Skardu.
- Heat and rainfall as the primary variables.
- NASA POWER as the initial working data source.
- Daily event exploration and monthly long-term trend analysis.
- Robust trend estimation and statistical significance reporting.
- Plain-language explanations backed by structured numeric results.
- Visible provenance, quality information, uncertainty, limitations, and export.

### Later source integrations

The source boundary should support future adapters for:

- NOAA Climate Data Online station observations.
- NASA AppEEARS spatial and temporal land-product samples.
- NASA GES DISC hydrology time series.
- NASA Giovanni or comparable external visualization links.

These sources must not be silently merged with NASA POWER data. Their source
type, units, temporal resolution, coverage, and processing must remain visible.

### Out of scope for the first version

- A global free-form analysis workspace.
- A production research data catalog.
- Automated causal claims.
- AI-generated numeric conclusions.
- Broad climate indicators beyond the focused heat/rainfall story.

## Guided scenes

1. **Mission briefing**
   Introduce the investigation and explain that a trend is not automatically a
   climate conclusion.
2. **Investigation area**
   Select a focused Pakistan/Indus preset or a supported coordinate and show
   location metadata.
3. **Evidence selection**
   Select temperature and rainfall, with definitions, units, source type, and
   time resolution.
4. **Time-series exploration**
   Inspect daily/monthly charts, baseline comparisons, data coverage, quality
   flags, and notable events.
5. **Change measurement**
   Report direction, rate per decade, confidence interval, and significance
   status.
6. **Variable and event connection**
   Compare heat and rainfall timelines and distinguish persistent trends,
   seasonality, and isolated extremes without claiming causation.
7. **Detective report**
   Present a concise verdict with evidence, limitations, source metadata, and
   CSV/JSON export.

## Architecture

The application should remain a focused Streamlit application with four
separable layers:

1. **Scene/state layer** — selected location, variables, period, investigation
   step, and whether enough evidence exists to proceed.
2. **Source adapters** — provider-specific retrieval and normalization into a
   common table plus provenance metadata.
3. **Analysis layer** — cleaning, quality checks, baselines, trend estimates,
   confidence intervals, significance tests, event detection, and comparison.
4. **Evidence/presentation layer** — charts, explanations, methods, source
   links, warnings, and report export.

The common analysis record should preserve:

`location, variable, source, units, temporal resolution, date coverage,
raw/processed status, quality flags, analysis method, result, uncertainty`.

The data flow is:

`selection -> source adapter -> cache/fetch -> normalize and validate ->
analyze -> render evidence -> proceed -> report`.

NASA POWER remains the initial default because the existing
`nasa_api.py` adapter already retrieves the core daily variables. Additional
providers should implement the same boundary rather than adding provider logic
directly to the UI.

Natural-language text must be generated from structured analysis results and
include the underlying values and caveats. It must not be the source of a
numeric conclusion.

## Data and statistical method

Initial variables:

- Temperature: NASA POWER `T2M`, `T2M_MAX`, and `T2M_MIN`.
- Rainfall: NASA POWER `PRECTOTCORR`.
- Context: relative humidity and solar radiation, clearly labeled as context
  rather than the primary trend evidence.

Daily values remain available for event inspection. Monthly means/totals are
used for long-term trend analysis to reduce day-to-day noise. A reference
baseline is used so seasonal patterns are not mislabeled as long-term change.

The analysis should:

- Report change per decade rather than only an array-index slope.
- Use a robust Theil–Sen slope where appropriate.
- Use a Mann–Kendall significance test and report a p-value or clear confidence
  category.
- Apply explicit minimum-coverage and missing-data rules.
- Treat rainfall as intermittent and skewed: show both seasonal/total change
  and event-frequency change.
- Retain the current `>2σ` logic only as an event-screening signal, never as
  proof of a statistically significant trend.
- Distinguish persistent trend, seasonal pattern, and isolated extreme event.
- Show source agreement/disagreement rather than silently combining incompatible
  measurements.

Every chart and report must expose period, units, aggregation, source, missing
data handling, and method.

## Reliability and user experience

- Provider errors show the affected source and actionable retry guidance.
- Empty, sparse, or invalid results cannot produce a successful-looking chart.
- The measurement scene is blocked when coverage or quality is insufficient.
- Observation, satellite-derived, and reanalysis/model data use distinct labels.
- Statistical warnings explain seasonality, autocorrelation, short records,
  missing periods, and multiple comparisons in plain language.
- Reports record location, date range, variables, source endpoint/version,
  transformations, method, and generation timestamp.

## Validation strategy

- Unit tests cover normalization, trend calculations, confidence/significance,
  event classification, and report metadata.
- Fixtures cover missing values, short windows, seasonal series, zero rainfall,
  constant series, and extreme outliers.
- Integration tests cover provider failures and cached responses.
- One deterministic end-to-end fixture completes the guided investigation.
- A usability check verifies that a first-time user can reach and understand a
  defensible verdict in a short guided flow and export the evidence.

## Success criteria

A student or general user can select an Indus-region location, inspect heat and
rainfall evidence, understand the measured rate and significance status, see
the limitations, and export a reproducible report without reading source code.

