# NOAA Station Comparison Design

## Status

Approved conceptually; implementation has not started.

## Goal

Add an honest NOAA Climate Data Online comparison path to EarthWatch AI without
silently merging station observations with NASA POWER reanalysis data.

## Scope

### In scope

- NOAA CDO API v2 station discovery and daily observations.
- Secure local token loading from `NOAA_CDO_TOKEN`.
- A local `.env` file for development only, ignored by Git.
- Separate NOAA and NASA POWER provenance, quality, coverage, units, and trend
  results.
- A comparison view that reports agreement or disagreement.
- Explicit no-station and missing-token states.
- Mocked adapter and comparison tests.
- README updates after the implementation is verified.

### Out of scope

- Storing credentials in source code, README, test fixtures, or Git history.
- Silently substituting NASA POWER when NOAA has no station coverage.
- Treating station observations and reanalysis as identical measurements.
- AppEEARS, GES DISC, or Giovanni implementation in this phase.

## Credential handling

- Read the token from the local `NOAA_CDO_TOKEN` environment variable.
- Support a developer `.env` file locally, but never commit that file.
- Add `.env` to `.gitignore`.
- Add `.env.example` containing only:

```text
NOAA_CDO_TOKEN=
```

- Raise a clear configuration error when the token is absent.
- Never display or log the token.

## Data flow

`selected coordinate -> NOAA station discovery -> station selection ->
daily observation request -> normalize -> validate -> analyze separately ->
compare with NASA POWER -> render provenance and limitations`.

The adapter must preserve the station ID, station name, measurement type,
original units, date coverage, quality information, and API endpoint in
`SourceMetadata` or an equivalent station metadata object.

## Adapter behavior

Create `noaa_api.py` with:

- explicit request timeout;
- explicit HTTP error propagation;
- token header handling;
- station search near the selected coordinate;
- daily observation retrieval for a selected station and date range;
- clear errors for missing token, no station, empty response, malformed payload,
  or unsupported measurement units;
- deterministic normalization into the analysis input contract.

The adapter must not fabricate a station result. If no suitable station is
available for a Pakistan/Indus location, the UI must state that comparison is
unavailable.

## Comparison behavior

NASA POWER and NOAA results remain separate analysis records. The comparison
must show:

- source and processing type;
- station ID and location for NOAA;
- units and temporal resolution;
- valid coverage and sample count;
- trend rate and confidence interval;
- p-value/significance status;
- agreement, disagreement, or insufficient-overlap status.

The comparison text must not claim causation. It should explain that NOAA is an
in-situ station record while NASA POWER is a reanalysis estimate, and that
different periods, locations, and measurement definitions can explain
disagreement.

## UI behavior

Add a clearly labeled optional NOAA comparison section after NASA evidence is
valid. The section must provide:

- a station selector when multiple stations are available;
- a loading state;
- a missing-token configuration message;
- a no-station message;
- side-by-side source cards and charts;
- a source-agreement explanation;
- no NOAA chart or verdict when the NOAA response is invalid.

The existing NASA-only wizard remains usable when NOAA comparison is unavailable.

## Testing

Add tests for:

- missing token;
- station discovery normalization;
- observation payload normalization;
- API errors and empty results;
- unit conversion and unsupported units;
- provenance preservation;
- separate NASA/NOAA trend results;
- agreement, disagreement, and insufficient-overlap outcomes;
- UI-safe behavior when NOAA is unavailable.

All tests must use mocked responses and must not contain the real token.

## Documentation

After implementation and verification:

- mark NOAA station comparison as implemented in `README.md`;
- document `NOAA_CDO_TOKEN` setup without including a value;
- document station-vs-reanalysis limitations;
- keep AppEEARS, GES DISC, and Giovanni listed as planned.

