import json
import os
from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st

from analyzer import analyze_climate_data
from nasa_api import fetch_nasa_climate_data
from noaa_api import (
    MissingNOAATokenError,
    NOAAAPIError,
    NoStationsFoundError,
    fetch_noaa_observations,
    search_stations,
)
from scene_state import WizardStep, advance_step, can_render_evidence, retreat_step
from source_comparison import compare_temperature_sources

st.set_page_config(
    page_title="EarthWatch AI | NASA Space Apps",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    div[data-testid="stMetric"] { background-color: rgba(28,35,51,.65);
      border: 1px solid rgba(99,179,237,.22); padding: 16px 20px;
      border-radius: 12px; }
    .insight-card { background-color: rgba(28,35,51,.5); border-left: 4px solid #38bdf8;
      padding: 14px 18px; border-radius: 8px; margin-bottom: 10px; }
    .insight-title { font-weight: 700; color: #7dd3fc; font-size: .95rem; margin-bottom: 4px; }
    </style>
    """,
    unsafe_allow_html=True,
)

PRESET_LOCATIONS = {
    "Karachi, Pakistan": (24.8607, 67.0011),
    "Thatta / Indus Delta, Pakistan": (24.7475, 67.9235),
    "Lahore, Pakistan": (31.5204, 74.3587),
    "Islamabad, Pakistan": (33.6844, 73.0479),
    "Skardu (Glacial Region), Pakistan": (35.2971, 75.6333),
    "Custom Coordinates": None,
}


def _chart_frame(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    chart = frame.loc[:, columns].copy().reset_index()
    chart = chart.rename(columns={chart.columns[0]: "Date"})
    chart["Date"] = pd.to_datetime(chart["Date"], errors="coerce")
    return chart.dropna(subset=["Date"]).sort_values("Date")


def _set_step(step: WizardStep) -> None:
    st.session_state.wizard_step = step.value


def _step() -> WizardStep:
    return WizardStep(st.session_state.get("wizard_step", WizardStep.BRIEFING.value))


def _progress(step: WizardStep) -> None:
    labels = ["1 · Briefing", "2 · Mission setup", "3 · Evidence", "4 · Verdict"]
    st.progress(step.value / 4, text=f"Step {step.value} of 4 · {labels[step.value - 1]}")


with st.sidebar:
    st.markdown("## 🛰️ EarthWatch AI")
    st.caption("NASA Space Apps Challenge • Karachi")
    st.divider()
    selected_city = st.selectbox("📍 Target Location", list(PRESET_LOCATIONS), index=0)
    if selected_city == "Custom Coordinates":
        col_lat, col_lon = st.columns(2)
        lat = col_lat.number_input("Latitude", value=24.8607, format="%.4f")
        lon = col_lon.number_input("Longitude", value=67.0011, format="%.4f")
    else:
        lat, lon = PRESET_LOCATIONS[selected_city]
    years_back = st.slider("📅 Historical Window (Years)", 1, 10, 3)
    st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}), zoom=7, use_container_width=True)
    st.caption(f"Coordinates: `{lat:.4f}° N, {lon:.4f}° E`")
    st.divider()
    st.markdown("**Data Source:** NASA Langley Research Center (LaRC) POWER Project API")

step = _step()
_progress(step)
st.title("🛰️ EarthWatch AI — Earth-system trend detective")
st.caption("A four-step investigation: brief → choose evidence → inspect signals → deliver a verdict.")

if step is WizardStep.BRIEFING:
    st.subheader("Step 1 · Mission briefing")
    st.markdown(
        "**Mission:** detect defensible climate signals from NASA POWER reanalysis.\n\n"
        "**Evidence:** daily reanalysis observations aggregated into monthly trends.\n\n"
        "**Guardrail:** incomplete coverage cannot produce a verdict."
    )
    st.info("Choose a location and historical window in the sidebar, then start the investigation.")
    if st.button("🚀 Start investigation", type="primary", use_container_width=True):
        _set_step(WizardStep.SELECTION)
        st.rerun()
    st.stop()

end_dt = date.today() - timedelta(days=5)
start_dt = end_dt.replace(year=end_dt.year - years_back)

if step is WizardStep.SELECTION:
    st.subheader("Step 2 · Location and date selection")
    st.info(
        f"Ready to investigate **{selected_city}** from **{start_dt:%b %d, %Y}** "
        f"through **{end_dt:%b %d, %Y}**."
    )
    st.caption("Adjust the sidebar controls before continuing. NASA data is not fetched until you continue.")
    back, forward = st.columns(2)
    if back.button("← Back to briefing", use_container_width=True):
        _set_step(retreat_step(step))
        st.rerun()
    if forward.button("Continue to evidence →", type="primary", use_container_width=True):
        with st.spinner(f"Downloading NASA POWER reanalysis for {selected_city}..."):
            try:
                raw_df, source = fetch_nasa_climate_data(
                    lat, lon, start_dt.strftime("%Y%m%d"), end_dt.strftime("%Y%m%d")
                )
                st.session_state.analysis = analyze_climate_data(raw_df, selected_city, source)
                st.session_state.analysis_error = None
            except (requests.RequestException, ValueError) as exc:
                st.session_state.analysis = None
                st.session_state.analysis_error = str(exc)
        _set_step(WizardStep.EVIDENCE)
        st.rerun()
    st.stop()

res = st.session_state.get("analysis")
if res is None:
    st.error(f"Could not retrieve NASA data: {st.session_state.get('analysis_error', 'unknown error')}")
    st.caption("Return to mission setup to try again with another location or date window.")
    if st.button("← Back to mission setup", use_container_width=True):
        _set_step(WizardStep.SELECTION)
        st.rerun()
    st.stop()

if not res["evidence_valid"]:
    st.subheader("Step 3 · Evidence coverage gate")
    quality = res["quality"]
    st.error("⚠️ Evidence coverage is insufficient for a normal verdict.")
    st.warning(
        f"Only {quality.valid_count:,} of {quality.total_count:,} observations are usable "
        f"({quality.coverage_fraction:.1%} coverage; minimum is 80%). "
        "Widen the date range or choose another location."
    )
    st.caption("No KPIs, trend charts, event verdict, or report scene is shown for this run.")
    if st.button("← Back to mission setup", use_container_width=True):
        _set_step(WizardStep.SELECTION)
        st.rerun()
    st.stop()

df = res["df"]
monthly = res["monthly"]
source = res.get("source")

if step is WizardStep.EVIDENCE:
    st.subheader("Step 3 · Evidence and provenance")
    cols = st.columns(4)
    cols[0].metric("Data type", "Daily reanalysis")
    cols[1].metric("Coverage", f"{res['quality'].coverage_fraction:.1%}")
    cols[2].metric("Observations", f"{res['quality'].valid_count:,}")
    cols[3].metric("Resolution", source.temporal_resolution if source else "Daily")
    if source:
        st.caption(
            f"**Source:** {source.provider} · **Variable:** {source.variable} ({source.units}) · "
            f"**Method:** {source.processing} · **Coverage:** {source.coverage_start} → {source.coverage_end}"
        )
    st.success(f"Evidence accepted: {res['quality'].coverage_fraction:.1%} valid daily coverage.")
    st.caption("Normalized, finite observations are aggregated to monthly summaries before screening.")
    st.subheader("Signals and screening evidence")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Mean Temperature", f"{res['avg_temp']:.1f} °C", f"{res['temp_delta_30d']:+.1f} °C (Last 30d)")
    k2.metric("Peak Max / Feels-Like", f"{res['max_temp']:.1f} °C", f"Feels like {res['max_feels_like']:.1f} °C")
    k3.metric("Cumulative Rainfall", f"{res['total_rain']:.1f} mm", f"Avg Humidity: {res['avg_humidity']:.0f}%")
    k4.metric("Unusual Weather Days", f"{res['anomaly_count']} days", f"{res['anomaly_count']/len(df)*100:.1f}% of window")
    t1, t2 = st.columns(2)
    with t1:
        st.markdown("**Daily temperature envelope (°C)**")
        st.line_chart(_chart_frame(df, ["Temp_Max", "Temp_Avg", "Temp_Min"]), x="Date", y=["Temp_Max", "Temp_Avg", "Temp_Min"])
    with t2:
        st.markdown("**Monthly rainfall (mm)**")
        st.bar_chart(_chart_frame(monthly, ["Rainfall_mm"]), x="Date", y="Rainfall_mm")
    with st.expander("Optional NOAA station comparison", expanded=False):
        st.caption(
            "NOAA observations are kept separate from NASA POWER reanalysis. "
            "The comparison is only available when NOAA_CDO_TOKEN is configured."
        )
        if not os.environ.get("NOAA_CDO_TOKEN", "").strip():
            st.info("NOAA comparison is unavailable in this run because no token is configured.")
        elif st.button("Compare with nearest NOAA station", use_container_width=True):
            with st.spinner("Finding a nearby NOAA station and loading observations..."):
                try:
                    stations = search_stations(
                        lat, lon, start_dt.isoformat(), end_dt.isoformat(), limit=1
                    )
                    noaa_df, noaa_source = fetch_noaa_observations(
                        stations[0], start_dt.isoformat(), end_dt.isoformat()
                    )
                    st.session_state.noaa_comparison = compare_temperature_sources(
                        df, noaa_df, source, noaa_source, selected_city
                    )
                    st.session_state.noaa_error = None
                except (
                    MissingNOAATokenError,
                    NOAAAPIError,
                    NoStationsFoundError,
                    ValueError,
                ) as exc:
                    st.session_state.noaa_comparison = None
                    st.session_state.noaa_error = str(exc)
            st.rerun()
        comparison = st.session_state.get("noaa_comparison")
        if comparison:
            st.success(comparison.message)
            c1, c2, c3 = st.columns(3)
            c1.metric("Comparison status", comparison.status.replace("_", " ").title())
            c2.metric("NASA rate", f"{comparison.nasa_trend.slope_per_decade:+.2f} °C/decade")
            c3.metric("NOAA rate", f"{comparison.noaa_trend.slope_per_decade:+.2f} °C/decade")
            st.caption(
                f"Overlapping daily dates: {comparison.overlap_count:,}. "
                "Agreement here means direction only; it is not causal proof."
            )
        elif st.session_state.get("noaa_error"):
            st.error(f"NOAA comparison failed: {st.session_state.noaa_error}")
    back, forward = st.columns(2)
    if back.button("← Back to mission setup", use_container_width=True):
        _set_step(WizardStep.SELECTION)
        st.rerun()
    if forward.button("Continue to verdict →", type="primary", use_container_width=True):
        _set_step(advance_step(step, evidence_valid=res["evidence_valid"]))
        st.rerun()
    st.stop()

if not can_render_evidence(step, res["evidence_valid"]):
    st.stop()

st.subheader("Step 4 · Final detective verdict")
st.title(f"🌍 {selected_city}")
st.metric("Climate Signal Status", f"{res['stress_color']} {res['stress_level']}")
st.info(
    f"**{res['stress_color']} {res['stress_level']}** — {selected_city} shows a "
    f"**{res['trends']['Temp_Avg'].significance.value.replace('_', ' ')}** temperature trend signal "
    "in this screening window. This is not causal attribution."
)
st.subheader("Robust trend evidence")
trend_rows = [
    {"Signal": name, "Rate / decade": f"{trend.slope_per_decade:+.2f}",
     "95% range": f"[{trend.lower_bound:+.2f}, {trend.upper_bound:+.2f}]",
     "p-value": f"{trend.p_value:.3f}", "Evidence": trend.significance.value.replace("_", " "),
     "Samples": trend.sample_count}
    for name, trend in res["trends"].items()
]
st.dataframe(pd.DataFrame(trend_rows), hide_index=True, use_container_width=True)
st.caption(f"Heat events: {res['event_summary']['heat_spike_count']} · Heavy-rain events: {res['event_summary']['heavy_rain_count']}")
with st.expander("Limitations and interpretation guardrails", expanded=True):
    for warning in res["warnings"]:
        st.markdown(f"- {warning.message if hasattr(warning, 'message') else warning}")
    st.markdown("- Reanalysis is a modeled estimate, not a local weather-station measurement.")
st.download_button("⬇️ Download NASA CSV", df.to_csv().encode("utf-8"), "earthwatch_nasa_data.csv", "text/csv")
st.download_button("⬇️ Download analysis report (JSON)", json.dumps(res["report"].to_dict(), indent=2), "earthwatch_analysis_report.json", "application/json")
if st.button("← Back to evidence", use_container_width=True):
    _set_step(retreat_step(step))
    st.rerun()
