import json

import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta
from nasa_api import fetch_nasa_climate_data
from analyzer import analyze_climate_data
from scene_state import Scene, can_show_analysis, transition

st.set_page_config(
    page_title="EarthWatch AI | NASA Space Apps",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for clean metric cards and modern typography
st.markdown("""
<style>
    div[data-testid="stMetric"] {
        background-color: rgba(28, 35, 51, 0.65);
        border: 1px solid rgba(99, 179, 237, 0.22);
        padding: 16px 20px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    .insight-card {
        background-color: rgba(28, 35, 51, 0.5);
        border-left: 4px solid #38bdf8;
        padding: 14px 18px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .insight-title {
        font-weight: 700;
        color: #7dd3fc;
        font-size: 0.95rem;
        margin-bottom: 4px;
    }
</style>
""", unsafe_allow_html=True)

PRESET_LOCATIONS = {
    "Karachi, Pakistan": (24.8607, 67.0011),
    "Thatta / Indus Delta, Pakistan": (24.7475, 67.9235),
    "Lahore, Pakistan": (31.5204, 74.3587),
    "Islamabad, Pakistan": (33.6844, 73.0479),
    "Skardu (Glacial Region), Pakistan": (35.2971, 75.6333),
    "Custom Coordinates": None
}

def _chart_frame(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Return chart data with a finite, explicit date axis for Streamlit."""
    chart = frame.loc[:, columns].copy().reset_index()
    chart = chart.rename(columns={chart.columns[0]: "Date"})
    chart["Date"] = pd.to_datetime(chart["Date"], errors="coerce")
    return chart.dropna(subset=["Date"]).sort_values("Date")


# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.markdown("## 🛰️ EarthWatch AI")
    st.caption("NASA Space Apps Challenge • Karachi")
    st.divider()

    selected_city = st.selectbox("📍 Target Location", list(PRESET_LOCATIONS.keys()), index=0)

    if selected_city == "Custom Coordinates":
        col_lat, col_lon = st.columns(2)
        lat = col_lat.number_input("Latitude", value=24.8607, format="%.4f")
        lon = col_lon.number_input("Longitude", value=67.0011, format="%.4f")
    else:
        lat, lon = PRESET_LOCATIONS[selected_city]

    years_back = st.slider("📅 Historical Window (Years)", min_value=1, max_value=10, value=3)

    # Mini location map preview
    st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}), zoom=7, use_container_width=True)
    st.caption(f"Coordinates: `{lat:.4f}° N, {lon:.4f}° E`")
    st.divider()
    st.markdown("**Data Source:** NASA Langley Research Center (LaRC) POWER Project API")

# --- DATE RANGE ---
end_dt = date.today() - timedelta(days=5)
start_dt = end_dt.replace(year=end_dt.year - years_back)

# --- MISSION FRAMING ---
st.title("🛰️ EarthWatch AI — Earth-system trend detective")
st.markdown(
    "**Mission:** detect defensible climate signals from NASA POWER telemetry. "
    "**Evidence:** daily reanalysis observations aggregated into monthly trends. "
    "**Guardrail:** incomplete coverage cannot produce a verdict."
)
st.progress(0.25, text="Step 1 of 4 · Choose a location and evidence window")
st.info(
    f"Targeting **{selected_city}** from **{start_dt.strftime('%b %d, %Y')}** "
    f"through **{end_dt.strftime('%b %d, %Y')}**."
)

# --- FETCH & ANALYZE ---
with st.spinner(f"Downloading NASA Earth Observation telemetry for {selected_city}..."):
    try:
        raw_df, source = fetch_nasa_climate_data(lat, lon, start_dt.strftime("%Y%m%d"), end_dt.strftime("%Y%m%d"))
        res = analyze_climate_data(raw_df, selected_city, source)
    except (requests.RequestException, ValueError) as e:
        st.error(f"Could not retrieve NASA data: {e}")
        st.stop()

scene = transition(Scene.LOADING, evidence_valid=res["evidence_valid"])

# Coverage is a hard gate: do not show derived KPIs, charts, or a verdict.
if not can_show_analysis(scene, res["evidence_valid"]):
    st.progress(0.50, text="Step 2 of 4 · Validate evidence coverage")
    st.error("⚠️ Evidence coverage is insufficient for a normal verdict.")
    quality = res["quality"]
    st.warning(
        f"Only {quality.valid_count:,} of {quality.total_count:,} observations are "
        f"usable ({quality.coverage_fraction:.1%} coverage; minimum is 80%). "
        "Download the source data or widen the date range before interpreting trends."
    )
    st.caption("No KPIs, trend charts, event verdict, or report scene is shown for this run.")
    st.stop()

df = res["df"]
monthly = res["monthly"]

# --- EVIDENCE AND PROVENANCE ---
st.progress(0.50, text="Step 2 of 4 · Evidence accepted — review provenance")
st.subheader("Step 2 · Evidence & provenance")
source = res.get("source")
source_cols = st.columns(4)
source_cols[0].metric("Data type", "Daily reanalysis")
source_cols[1].metric("Coverage", f"{res['quality'].coverage_fraction:.1%}")
source_cols[2].metric("Observations", f"{res['quality'].valid_count:,}")
source_cols[3].metric("Resolution", source.temporal_resolution if source else "Daily")
if source:
    st.caption(
        f"**Source:** {source.provider} · **Variable:** {source.variable} ({source.units}) · "
        f"**Method:** {source.processing} · **Coverage:** {source.coverage_start} → {source.coverage_end}"
    )
st.caption(
    "NASA POWER observations are normalized, checked for finite values, and aggregated to monthly "
    "summaries before trend screening."
)

# --- HEADER BANNER ---
head_left, head_right = st.columns([3, 1])
with head_left:
    st.title(f"🌍 {selected_city}")
    st.caption(f"Satellite & Reanalysis Telemetry • {start_dt.strftime('%b %d, %Y')} to {end_dt.strftime('%b %d, %Y')} ({len(df):,} days)")
with head_right:
    st.metric("Climate Signal Status", f"{res['stress_color']} {res['stress_level']}")

st.success(
    f"Evidence accepted: {res['quality'].coverage_fraction:.1%} valid daily coverage. "
    "The following trends are screening evidence, not causal attribution."
)

# --- TOP KPI ROW ---
st.progress(0.75, text="Step 3 of 4 · Inspect signals and statistical evidence")
st.subheader("Step 3 · Signals and screening evidence")
k1, k2, k3, k4 = st.columns(4)
k1.metric(
    "Mean Temperature",
    f"{res['avg_temp']:.1f} °C",
    f"{res['temp_delta_30d']:+.1f} °C (Last 30d)"
)
k2.metric(
    "Peak Max / Feels-Like",
    f"{res['max_temp']:.1f} °C",
    f"Feels like {res['max_feels_like']:.1f} °C",
    delta_color="off"
)
k3.metric(
    "Cumulative Rainfall",
    f"{res['total_rain']:.1f} mm",
    f"Avg Humidity: {res['avg_humidity']:.0f}%"
)
k4.metric(
    "Unusual Weather Days",
    f"{res['anomaly_count']} days",
    f"{(res['anomaly_count']/len(df)*100):.1f}% of window",
    delta_color="inverse"
)

st.write("")

# --- AUTOMATED PLAIN-ENGLISH BRIEFING ---
st.subheader("🧠 Automated Environmental Briefing")
b_cols = st.columns(3)
for idx, insight in enumerate(res["insights"]):
    with b_cols[idx]:
        st.markdown(f"""
        <div class="insight-card">
            <div class="insight-title">{insight['title']}</div>
            <div>{insight['body']}</div>
        </div>
        """, unsafe_allow_html=True)

st.write("")

# --- TABBED VISUALIZATIONS ---
tab1, tab2, tab3 = st.tabs([
    "📈 Daily Trends & Heat Index",
    "🌧️ Monthly & Monsoon Patterns",
    "⚠️ Unusual Events & Data Export"
])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Daily Temperature Envelope (°C)**")
        daily_temperature = _chart_frame(df, ["Temp_Max", "Temp_Avg", "Temp_Min"])
        st.line_chart(daily_temperature, x="Date", y=["Temp_Max", "Temp_Avg", "Temp_Min"], color=["#ef4444", "#f59e0b", "#38bdf8"])
    with c2:
        st.markdown("**Daily Precipitation (mm/day)**")
        st.bar_chart(_chart_frame(df, ["Rainfall_mm"]), x="Date", y="Rainfall_mm", color="#3b82f6")

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("**Relative Humidity (%)**")
        st.area_chart(_chart_frame(df, ["Humidity_pct"]), x="Date", y="Humidity_pct", color="#14b8a6")
    with c4:
        st.markdown("**Surface Solar Irradiance (kWh/m²/day)**")
        st.line_chart(_chart_frame(df, ["Solar_kWh_m2"]), x="Date", y="Solar_kWh_m2", color="#eab308")

with tab2:
    m1, m2 = st.columns(2)
    with m1:
        st.markdown("**Monthly Total Rainfall (mm) — Spot Monsoon Surges**")
        monthly_rain = _chart_frame(monthly, ["Rainfall_mm"])
        st.bar_chart(monthly_rain, x="Date", y="Rainfall_mm", color="#2563eb")
    with m2:
        st.markdown("**Monthly Mean vs. Peak Temperature (°C)**")
        monthly_temperature = _chart_frame(monthly, ["Temp_Max", "Temp_Avg"])
        st.line_chart(monthly_temperature, x="Date", y=["Temp_Max", "Temp_Avg"], color=["#f97316", "#facc15"])

with tab3:
    top_bar_l, top_bar_r = st.columns([3, 1])
    with top_bar_l:
        st.markdown(f"**Detected Statistical Anomalies ({len(res['all_anomalies'])} events > 2σ from local baseline)**")
    with top_bar_r:
        csv_bytes = df.to_csv().encode("utf-8")
        st.download_button(
            label="⬇️ Download NASA CSV",
            data=csv_bytes,
            file_name=f"earthwatch_{selected_city.split(',')[0].lower()}_nasa_data.csv",
            mime="text/csv",
            use_container_width=True
        )

    if res["all_anomalies"].empty:
        st.success("No extreme weather anomalies detected in the selected window.")
    else:
        display_cols = ["Event_Type", "Temp_Max", "Feels_Like_Max", "Rainfall_mm", "Humidity_pct"]
        st.dataframe(res["all_anomalies"][display_cols].round(1), use_container_width=True)

    st.markdown("**Robust trend evidence**")
    st.caption("Legend: ✅ significant (p < 0.05) · ◻️ not significant · ⏳ insufficient evidence")
    trend_rows = []
    for name, trend in res["trends"].items():
        trend_rows.append(
            {
                "Signal": name,
                "Rate / decade": f"{trend.slope_per_decade:+.2f}",
                "95% range": f"[{trend.lower_bound:+.2f}, {trend.upper_bound:+.2f}]",
                "p-value": f"{trend.p_value:.3f}",
                "Evidence": trend.significance.value.replace("_", " "),
                "Samples": trend.sample_count,
            }
        )
    st.dataframe(pd.DataFrame(trend_rows), hide_index=True, use_container_width=True)
    st.caption(
        f"Heat events: {res['event_summary']['heat_spike_count']} · "
        f"Heavy-rain events: {res['event_summary']['heavy_rain_count']}"
    )

st.progress(1.0, text="Step 4 of 4 · Read the detective verdict and export the report")
st.subheader("Step 4 · Detective verdict")
verdict_text = (
    f"**{res['stress_color']} {res['stress_level']}** — "
    f"{selected_city} shows a **{res['trends']['Temp_Avg'].significance.value.replace('_', ' ')}** "
    "temperature trend signal in this screening window. "
    "Use the slope and p-value above for the statistical detail; this is not causal attribution."
)
st.info(verdict_text)
with st.expander("Limitations and interpretation guardrails", expanded=True):
    for warning in res["warnings"]:
        message = warning.message if hasattr(warning, "message") else warning
        st.markdown(f"- {message}")
    st.markdown("- Reanalysis is a modeled estimate, not a local weather-station measurement.")
    st.markdown("- Event thresholds flag unusual days; they do not establish climate causation.")

    report_json = json.dumps(res["report"].to_dict(), indent=2)
    st.download_button(
        "⬇️ Download analysis report (JSON)",
        data=report_json,
        file_name="earthwatch_analysis_report.json",
        mime="application/json",
        use_container_width=True,
    )
