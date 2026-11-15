import streamlit as st
import pandas as pd
from datetime import date, timedelta
from nasa_api import fetch_nasa_climate_data
from analyzer import analyze_climate_data

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

# --- FETCH & ANALYZE ---
end_dt = date.today() - timedelta(days=5)
start_dt = end_dt.replace(year=end_dt.year - years_back)

with st.spinner(f"Downloading NASA Earth Observation telemetry for {selected_city}..."):
    try:
        raw_df, _source = fetch_nasa_climate_data(lat, lon, start_dt.strftime("%Y%m%d"), end_dt.strftime("%Y%m%d"))
        res = analyze_climate_data(raw_df, selected_city)
    except Exception as e:
        st.error(f"Could not retrieve NASA data: {e}")
        st.stop()

df = res["df"]
monthly = res["monthly"]

# --- HEADER BANNER ---
head_left, head_right = st.columns([3, 1])
with head_left:
    st.title(f"🌍 {selected_city}")
    st.caption(f"Satellite & Reanalysis Telemetry • {start_dt.strftime('%b %d, %Y')} to {end_dt.strftime('%b %d, %Y')} ({len(df):,} days)")
with head_right:
    st.metric("Climate Signal Status", f"{res['stress_color']} {res['stress_level']}")

# --- TOP KPI ROW ---
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
        st.line_chart(df[["Temp_Max", "Temp_Avg", "Temp_Min"]], color=["#ef4444", "#f59e0b", "#38bdf8"])
    with c2:
        st.markdown("**Daily Precipitation (mm/day)**")
        st.bar_chart(df["Rainfall_mm"], color="#3b82f6")
        
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("**Relative Humidity (%)**")
        st.area_chart(df["Humidity_pct"], color="#14b8a6")
    with c4:
        st.markdown("**Surface Solar Irradiance (kWh/m²/day)**")
        st.line_chart(df["Solar_kWh_m2"], color="#eab308")

with tab2:
    m1, m2 = st.columns(2)
    with m1:
        st.markdown("**Monthly Total Rainfall (mm) — Spot Monsoon Surges**")
        st.bar_chart(monthly["Rainfall_mm"], color="#2563eb")
    with m2:
        st.markdown("**Monthly Mean vs. Peak Temperature (°C)**")
        st.line_chart(monthly[["Temp_Max", "Temp_Avg"]], color=["#f97316", "#facc15"])

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
