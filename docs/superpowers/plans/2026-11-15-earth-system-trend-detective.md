# Earth System Trend Detective Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a guided Pakistan/Indus heat-and-rainfall trend investigation in the existing Streamlit app, with reproducible data provenance, robust trend statistics, visible uncertainty, and exportable evidence.

**Architecture:** Keep Streamlit as the presentation shell, but move provider retrieval, normalized records, and scientific calculations behind small typed boundaries. NASA POWER is the only live provider in this slice; the normalized source contract is designed so NOAA, AppEEARS, and GES DISC can be added later without putting provider logic in the UI.

**Tech Stack:** Python, Streamlit, pandas, NumPy, requests, SciPy (for Theil–Sen and Mann–Kendall support if available), pytest.

---

## File map

- Modify `nasa_api.py`: return a normalized NASA POWER dataset and provenance metadata; preserve Streamlit caching and explicit HTTP failures.
- Create `trend_models.py`: dataclasses and enums for source metadata, quality, normalized observations, trend results, and report payloads.
- Modify `analyzer.py`: retain heat-index and anomaly behavior while adding validation, monthly baseline preparation, robust trend estimation, significance classification, event classification, and report-ready structured results.
- Modify `app.py`: implement the seven guided scenes with `st.session_state`, gate later scenes on valid evidence, render source/method/warning metadata, and export CSV/JSON.
- Create `tests/conftest.py`: shared deterministic daily and monthly fixtures.
- Create `tests/test_nasa_api.py`: adapter normalization, missing-value, HTTP, and provenance tests using mocked responses.
- Create `tests/test_analyzer.py`: model, trend, significance, rainfall, quality, and event tests.
- Create `tests/test_app_flow.py`: deterministic Streamlit interaction smoke test or, if the installed Streamlit version does not support a stable app test API, a pure scene-state test around extracted state helpers.
- Modify `requirements.txt`: add only the statistical/testing dependency actually required by the implementation and keep existing pinned dependencies intact.
- Create `README.md` only if no project README exists: document startup, data sources, statistical caveats, and the guided flow.

## Task 1: Establish normalized source and analysis models

**Files:**
- Create: `trend_models.py`
- Test: `tests/test_analyzer.py`

- [ ] **Step 1: Write failing model tests**

Add tests that require a source metadata object to preserve provider, endpoint,
variable, units, temporal resolution, coverage, and processing status, and a
trend result to expose slope per decade, confidence bounds, p-value, sample
count, and a categorical significance label.

```python
from trend_models import Significance, SourceMetadata, TrendResult


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
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run:

```powershell
pytest tests/test_analyzer.py -q
```

Expected: FAIL because `trend_models.py` and its model types do not exist.

- [ ] **Step 3: Implement the models**

Use `dataclasses.dataclass` and an enum with exactly `SIGNIFICANT`,
`NOT_SIGNIFICANT`, and `INSUFFICIENT_EVIDENCE`. Add `QualitySummary`,
`SourceMetadata`, `TrendResult`, `AnalysisWarning`, and `AnalysisReport`
dataclasses with explicit types. Keep model fields serializable using
`dataclasses.asdict`.

- [ ] **Step 4: Run the focused tests**

Run:

```powershell
pytest tests/test_analyzer.py -q
```

Expected: PASS for the model tests.

- [ ] **Step 5: Commit**

```powershell
git add trend_models.py tests/test_analyzer.py
git commit -m "feat: add normalized trend analysis models"
```

## Task 2: Make NASA POWER retrieval explicit and testable

**Files:**
- Modify: `nasa_api.py`
- Create: `tests/conftest.py`
- Create: `tests/test_nasa_api.py`

- [ ] **Step 1: Add deterministic adapter tests**

Mock `requests.get` with a NASA POWER-shaped JSON response containing two dates,
one `-999.0` missing value, and the six requested parameters. Assert that the
adapter returns the existing analysis column names, a `DatetimeIndex` named
`Date`, floating-point values, and source metadata. Add a test that
`raise_for_status()` failures are surfaced as an exception rather than an
empty frame.

```python
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
    assert source.provider == "NASA POWER"
```

- [ ] **Step 2: Run the adapter tests and verify failure**

Run:

```powershell
pytest tests/test_nasa_api.py -q
```

Expected: FAIL because the current function returns only a DataFrame and does
not return a provenance object.

- [ ] **Step 3: Add the normalized adapter result**

Keep the public function name but return `(DataFrame, SourceMetadata)`. Preserve
the current request parameters and `st.cache_data`. Build the metadata from the
requested coordinates, date range, parameter list, and NASA POWER endpoint.
Continue to call `raise_for_status()`, use a timeout, replace `-999.0`, drop
invalid rows, and raise a clear `ValueError` if no valid rows remain.

- [ ] **Step 4: Update the existing call site**

Change `app.py` to unpack the tuple and pass both frame and metadata into the
analysis layer. Do not catch exceptions broadly; show the existing Streamlit
error and stop the app after the provider-specific exception is surfaced.

- [ ] **Step 5: Run adapter and import tests**

Run:

```powershell
pytest tests/test_nasa_api.py -q
python -c "import nasa_api"
```

Expected: all adapter tests pass and the import exits successfully.

- [ ] **Step 6: Commit**

```powershell
git add nasa_api.py app.py tests/conftest.py tests/test_nasa_api.py
git commit -m "feat: add provenance to NASA POWER adapter"
```

## Task 3: Implement validated robust trend analysis

**Files:**
- Modify: `analyzer.py`
- Modify: `requirements.txt`
- Modify: `tests/conftest.py`
- Modify: `tests/test_analyzer.py`

- [ ] **Step 1: Add failing statistical tests**

Create deterministic monthly fixtures with a known positive temperature trend,
an unchanging rainfall series, missing months, and a single large event. Test:

```python
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
```

- [ ] **Step 2: Run the analysis tests and verify failure**

Run:

```powershell
pytest tests/test_analyzer.py -q
```

Expected: FAIL because the current analyzer returns a raw slope and does not
provide trend results, coverage validation, or significance classification.

- [ ] **Step 3: Implement validation and monthly preparation**

Add small functions with explicit signatures:

```python
def validate_observations(df: pd.DataFrame) -> QualitySummary: ...
def prepare_monthly_analysis(df: pd.DataFrame) -> pd.DataFrame: ...
def calculate_trend(series: pd.Series, periods_per_year: float) -> TrendResult: ...
def classify_events(df: pd.DataFrame) -> pd.DataFrame: ...
```

Validate required columns, sorted unique dates, finite numeric values, and
minimum coverage before calculating a trend. Preserve daily data for event
inspection and aggregate monthly temperature means and rainfall totals.

- [ ] **Step 4: Implement robust statistics**

Use Theil–Sen slope and a Mann–Kendall significance test with a documented
fallback or a clear dependency error if the selected package does not provide
the required operation. Convert the slope to a per-decade rate using the actual
time spacing. Return confidence bounds, p-value, sample count, and
`INSUFFICIENT_EVIDENCE` when the record is too short or too sparse.

- [ ] **Step 5: Preserve and classify existing behavior**

Keep heat-index calculation and the existing insight fields needed by the UI.
Move anomaly labeling into `classify_events`, retaining `>2σ` as an event
screening rule only. Add event labels for heat spikes and heavy precipitation,
and include warnings that events are not proof of a long-term trend.

- [ ] **Step 6: Add the dependency only if required**

If the chosen Mann–Kendall implementation is not already importable, add its
exact pinned package to `requirements.txt`; do not install unrelated packages.
Run the dependency installation only after this manifest change.

- [ ] **Step 7: Run focused and regression tests**

Run:

```powershell
pytest tests/test_analyzer.py tests/test_nasa_api.py -q
```

Expected: all new and existing analysis/adapter tests pass.

- [ ] **Step 8: Commit**

```powershell
git add analyzer.py requirements.txt tests/conftest.py tests/test_analyzer.py
git commit -m "feat: add robust heat and rainfall trend analysis"
```

## Task 4: Extract guided scene state and evidence gating

**Files:**
- Modify: `app.py`
- Create: `tests/test_app_flow.py`

- [ ] **Step 1: Add failing state-transition tests**

Test a pure helper in `app.py` (or a small new `scene_state.py` module if
Streamlit imports make helpers difficult to test) that starts at `MISSION`,
requires a location before `EVIDENCE`, requires valid coverage before
`MEASURE`, and cannot reach `REPORT` from insufficient evidence.

```python
from scene_state import Scene, advance_scene, initial_scene_state
from trend_models import AnalysisReport, QualitySummary


def insufficient_report():
    return AnalysisReport(
        quality=QualitySummary(valid=False, coverage_fraction=0.25),
        trends={},
        warnings=["Insufficient coverage"],
    )


def test_scene_flow_requires_valid_evidence():
    state = initial_scene_state()
    assert state.scene == Scene.MISSION
    state = advance_scene(state, location="Thatta / Indus Delta")
    assert state.scene == Scene.EVIDENCE
    state = advance_scene(state, variables=["Temp_Avg", "Rainfall_mm"])
    assert state.scene == Scene.EXPLORE
    state = advance_scene(state, analysis=insufficient_report())
    assert state.scene == Scene.EXPLORE
```

Define `Scene`, `SceneState`, `initial_scene_state`, and `advance_scene` in a
new `scene_state.py` module rather than importing Streamlit from tests.
`advance_scene` accepts optional `location`, `variables`, and `analysis`
arguments and returns a new state. It must leave the state at `EXPLORE` when
`analysis.quality.valid` is false or any selected trend is
`INSUFFICIENT_EVIDENCE`.

- [ ] **Step 2: Run the scene tests and verify failure**

Run:

```powershell
pytest tests/test_app_flow.py -q
```

Expected: FAIL because the guided state and transition helpers do not exist.

- [ ] **Step 3: Implement typed scene state**

Create `scene_state.py` with an enum containing `MISSION`, `LOCATION`,
`EVIDENCE`, `EXPLORE`, `MEASURE`, `CONNECT`, and `REPORT`, plus a typed
`SceneState` dataclass. Store a `SceneState` instance in `st.session_state`,
but keep transitions and gates in pure functions. The state must hold selected
preset/coordinates, variables, date range, normalized data, metadata, analysis
report, and warnings.

- [ ] **Step 4: Render the first four scenes**

Replace the always-visible dashboard flow with a mission briefing, location
selection using the existing presets, evidence selection for temperature and
rainfall, and exploration charts. Keep the existing map and daily/monthly
charts where they support those scenes.

- [ ] **Step 5: Render measurement, connection, and report scenes**

Show per-variable rate per decade, confidence bounds, p-value/significance
label, coverage, and method. Add the heat/rainfall comparison chart and event
classification. The final report must show source metadata, warnings,
limitations, and JSON/CSV downloads.

- [ ] **Step 6: Add explicit provider failure UX**

Display a source-specific error and retry control. Do not render KPI cards or
verdict text when the fetch or validation step failed. Keep the existing
`st.stop()` behavior after the error.

- [ ] **Step 7: Run the scene and regression tests**

Run:

```powershell
pytest tests/test_app_flow.py tests/test_analyzer.py tests/test_nasa_api.py -q
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```powershell
git add app.py tests/test_app_flow.py
git commit -m "feat: add guided trend detective scenes"
```

## Task 5: Document use, sources, and scientific limitations

**Files:**
- Create or modify: `README.md`
- Modify: `app.py` only if help text or source links are needed

- [ ] **Step 1: Document startup and guided flow**

Include the exact commands:

```powershell
pip install -r requirements.txt
streamlit run app.py
```

Document the seven scenes, Pakistan/Indus scope, NASA POWER variables, CSV/JSON
exports, and how to interpret the significance labels.

- [ ] **Step 2: Document source boundaries**

Link NASA POWER, AppEEARS, NOAA CDO, GES DISC Hydrology Time Series, Giovanni,
and the NASA SeaWiFS time-series paper. State that future sources are not
silently combined and that reanalysis/model data are distinct from station or
satellite observations.

- [ ] **Step 3: Document limitations**

State that significance is not causation, rainfall requires special
interpretation, short or sparse records are insufficient, event screening is
not trend proof, and source coverage/quality affects conclusions.

- [ ] **Step 4: Commit**

```powershell
git add README.md app.py
git commit -m "docs: explain trend detective workflow and limitations"
```

## Task 6: Full verification and handoff

**Files:**
- No new source files; inspect all changed files and test outputs.

- [ ] **Step 1: Run formatting and static checks available in the repository**

Run the repository’s configured checks if present. At minimum run:

```powershell
python -m compileall app.py nasa_api.py analyzer.py trend_models.py
pytest -q
git --no-pager diff --check
```

Expected: compilation succeeds, all tests pass, and diff check produces no
output.

- [ ] **Step 2: Exercise the app manually**

Run:

```powershell
streamlit run app.py
```

Verify the default Thatta/Indus or Karachi path, a short invalid period, a
provider failure, an insufficient-evidence result, a significant result, and
CSV/JSON downloads. Stop the process using its specific process ID after the
checks.

- [ ] **Step 3: Confirm worktree and commit history**

Run:

```powershell
git --no-pager status --short
git --no-pager log -8 --oneline
```

Expected: no accidental generated files, secrets, or unrelated modifications;
each task has a focused commit with the required Copilot co-author trailer.
