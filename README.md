# EarthWatch AI — Earth-System Trend Detective

EarthWatch AI is an interactive NASA-powered investigation tool for exploring
temperature and rainfall signals across Pakistan and the Indus region. It is
designed for students and the public: choose a location, inspect the evidence,
measure a trend, and understand the limitations before reaching a conclusion.

## What is working now

- Interactive four-step investigation wizard:
  1. Mission briefing
  2. Location and historical-window selection
  3. Evidence, charts, and statistical screening
  4. Detective verdict and report export
- Pakistan and Indus-region presets, plus custom coordinates.
- Live daily data retrieval from the NASA POWER point API.
- Temperature, rainfall, humidity, and surface solar-radiation views.
- Daily event screening for unusual heat and heavy precipitation.
- Monthly aggregation for long-term screening.
- Theil–Sen slope estimates reported per decade.
- Mann–Kendall significance screening.
- Coverage and finite-value validation.
- Invalid or sparse evidence is blocked from producing a normal verdict.
- CSV data export and JSON analysis-report export.
- Automated tests covering the source adapter, analysis, data quality, report
  serialization, and wizard transitions.

## Important honesty statement

The current live source is **NASA POWER daily reanalysis data**. This is a
NASA Earth-science/model-derived estimate and is not the same as:

- a direct measurement from a local weather station;
- a single satellite instrument's raw observation; or
- an official climate or disaster warning.

The application does not fabricate weather observations. It requests the
selected coordinates and date range from NASA POWER, validates the returned
records, and calculates the displayed summaries from those records.

The results are **screening evidence**, not causal climate attribution. A
detected slope does not prove why the change occurred. A statistical
significance label applies only to the selected series and time window.
`ELEVATED`, `MODERATE`, and `STABLE` are application-level screening labels,
not official risk categories.

Rainfall is intermittent and skewed, so event counts and long-term rainfall
changes require additional interpretation. Short, sparse, or invalid records
are explicitly treated as insufficient evidence.

## Data and methods

The app requests these NASA POWER parameters:

| Parameter | Display use |
|---|---|
| `T2M` | Daily mean temperature |
| `T2M_MAX` | Daily maximum temperature |
| `T2M_MIN` | Daily minimum temperature |
| `PRECTOTCORR` | Corrected precipitation |
| `RH2M` | Relative humidity |
| `ALLSKY_SFC_SW_DWN` | Surface solar radiation |

Daily values are retained for event inspection. Monthly summaries are used for
trend screening. Theil–Sen estimates a robust slope, and the Mann–Kendall
screening test reports a p-value and evidence category. The app also shows
coverage, sample count, confidence bounds, source metadata, and limitations.

## Run locally

Requirements: Python 3.10+ and internet access for NASA POWER requests.

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open `http://localhost:8501`.

Run the tests:

```powershell
python -m pytest -q
```

## NASA Space Apps challenge connection

The project addresses the Earth System Trend Detective challenge by helping a
user investigate:

- what is changing;
- where it is changing;
- how much it is changing; and
- whether the selected signal is statistically significant.

The user can inspect the evidence and method instead of receiving an
unsupported black-box conclusion.

## Referenced resources

- [NASA POWER](https://power.larc.nasa.gov/)
- [NASA AppEEARS](https://appeears.earthdatacloud.nasa.gov/)
- [NOAA Climate Data Online](https://www.ncei.noaa.gov/cdo-web/)
- [NASA GES DISC Hydrology Time Series](https://disc.gsfc.nasa.gov/information/tools?title=Hydrology%20Time%20Series)
- [NASA Giovanni](https://giovanni.gsfc.nasa.gov/giovanni/)
- [NASA SeaWiFS time-series analysis paper](https://ntrs.nasa.gov/citations/20090042747)

AppEEARS, NOAA CDO, GES DISC, and Giovanni are documented reference resources
for planned source-comparison work. They are **not silently merged** into the
current NASA POWER analysis.

## Planned next phases

These are intentionally listed as planned rather than represented as already
implemented:

1. Add NOAA station observations as a separately labeled comparison source.
2. Add AppEEARS samples for selected land and vegetation products.
3. Add GES DISC hydrology time-series variables.
4. Add source-agreement comparisons and richer regional analysis.
5. Add deployment configuration and a public hosted instance.

Each future source will keep its own units, coverage, processing type, quality
flags, and provenance. The project will not claim multi-source conclusions
until those adapters and comparison tests exist.

## License and attribution

NASA data and services remain subject to their respective terms and
attribution requirements. This project is an educational NASA Space Apps
prototype.
