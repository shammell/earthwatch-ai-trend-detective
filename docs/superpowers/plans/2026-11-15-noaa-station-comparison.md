# NOAA Station Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a secure, separately labeled NOAA CDO station comparison to EarthWatch AI without merging station observations with NASA POWER reanalysis.

**Architecture:** Add a focused `noaa_api.py` adapter that reads `NOAA_CDO_TOKEN` from the environment, discovers/fetches station observations, and returns normalized data plus provenance. Add comparison helpers and an optional UI section; NASA-only behavior remains valid when NOAA is unavailable.

**Tech Stack:** Python, requests, pandas, Streamlit, python-dotenv only if already available, pytest.

---

## Task 1: Secure configuration and NOAA adapter

**Files:**
- Create: `noaa_api.py`
- Create: `.env.example`
- Modify: `.gitignore`
- Create: `tests/test_noaa_api.py`

- [ ] Add mocked tests for missing token, HTTP errors, empty results, station metadata, and normalized observations.
- [ ] Implement token lookup from `NOAA_CDO_TOKEN` or an explicit configuration error; never log the token.
- [ ] Implement station search and daily observations with timeout, API-key header, clear errors, station ID/name preservation, and `SourceMetadata(processing="NOAA station observation")`.
- [ ] Normalize NOAA observation fields to the existing analysis contract only when units are supported.
- [ ] Add `.env` and secret patterns to `.gitignore`; add only `NOAA_CDO_TOKEN=` to `.env.example`.
- [ ] Run `python -m pytest tests/test_noaa_api.py -q` and commit.

## Task 2: Separate source comparison

**Files:**
- Create: `source_comparison.py`
- Create: `tests/test_source_comparison.py`

- [ ] Add failing tests for agreement, disagreement, and insufficient overlap.
- [ ] Implement typed comparison results containing both source metadata, trend rates, significance, overlap count, and status.
- [ ] Ensure NASA and NOAA are analyzed independently and never concatenated as if they were identical observations.
- [ ] Run focused tests and commit.

## Task 3: Optional wizard UI

**Files:**
- Modify: `app.py`
- Modify: `requirements.txt` only if a missing dependency is required.
- Modify: `tests/test_scene_state.py` if state behavior changes.

- [ ] Add an optional NOAA comparison control after valid NASA evidence.
- [ ] Show missing-token, no-station, API-error, and unavailable-comparison messages without breaking NASA-only flow.
- [ ] Show separate NOAA/NASA cards, trends, coverage, and agreement status.
- [ ] Preserve the existing invalid-coverage hard gate and exports.
- [ ] Run the full test suite and compile checks; commit.

## Task 4: Documentation and secret verification

**Files:**
- Modify: `README.md`
- Verify: `.env`, `.gitignore`

- [ ] Document NOAA setup using `NOAA_CDO_TOKEN` without including its value.
- [ ] Mark NOAA comparison implemented only after live/mock verification.
- [ ] Keep AppEEARS, GES DISC, and Giovanni explicitly planned.
- [ ] Search tracked files for token-shaped secrets, run `git diff --check`, run `pytest -q`, and push the verified commits.

