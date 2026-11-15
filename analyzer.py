import numpy as np
import pandas as pd

from trend_models import SourceMetadata


def calculate_heat_index(temp_c: pd.Series, rh: pd.Series) -> pd.Series:
    """Approximates feels-like Heat Index in °C using Rothfusz regression."""
    t_f = temp_c * 9 / 5 + 32
    hi_f = (
        -42.379 + 2.04901523 * t_f + 10.14333127 * rh
        - 0.22475541 * t_f * rh - 0.00683783 * (t_f ** 2)
        - 0.05481717 * (rh ** 2) + 0.00122874 * (t_f ** 2) * rh
        + 0.00085282 * t_f * (rh ** 2) - 0.00000199 * (t_f ** 2) * (rh ** 2)
    )
    # Only apply heat index formula when temp >= 27°C and humidity >= 40%
    hi_c = (hi_f - 32) * 5 / 9
    return np.where((temp_c >= 27.0) & (rh >= 40.0), hi_c, temp_c)

def analyze_climate_data(
    df: pd.DataFrame, location_name: str, source: SourceMetadata | None = None
) -> dict:
    df = df.copy()
    df["Feels_Like_Max"] = calculate_heat_index(df["Temp_Max"], df["Humidity_pct"])
    
    # 1. Long-term temperature trend (°C/year)
    x = np.arange(len(df))
    temp_slope = np.polyfit(x, df["Temp_Avg"], 1)[0] * 365.25
    
    # 2. Recent 30-day shift vs full period baseline
    recent_30 = df.tail(30)
    temp_delta_30d = recent_30["Temp_Avg"].mean() - df["Temp_Avg"].mean()
    humidity_delta_30d = recent_30["Humidity_pct"].mean() - df["Humidity_pct"].mean()
    
    # 3. Anomaly detection (> 2 standard deviations)
    temp_thresh = df["Temp_Max"].mean() + 2 * df["Temp_Max"].std()
    heat_anomalies = df[df["Temp_Max"] > temp_thresh].copy()
    heat_anomalies["Event_Type"] = "Extreme Heat Spike"
    
    rain_thresh = max(15.0, df["Rainfall_mm"].mean() + 2 * df["Rainfall_mm"].std())
    rain_anomalies = df[df["Rainfall_mm"] > rain_thresh].copy()
    rain_anomalies["Event_Type"] = "Heavy Precipitation"
    
    all_anomalies = pd.concat([heat_anomalies, rain_anomalies]).sort_index(ascending=False)
    
    # 4. Monthly aggregation for seasonal/monsoon charts
    monthly = df.resample("ME").agg({
        "Temp_Avg": "mean",
        "Temp_Max": "max",
        "Rainfall_mm": "sum",
        "Humidity_pct": "mean",
        "Solar_kWh_m2": "mean"
    })
    monthly.index = monthly.index.strftime("%Y-%m")
    
    # 5. Climate stress indicator
    anomaly_rate = (len(all_anomalies) / len(df)) * 100
    if anomaly_rate > 4.5 or temp_slope > 0.15:
        stress_level, stress_color = "ELEVATED", "🔴"
    elif anomaly_rate > 2.5 or temp_slope > 0.05:
        stress_level, stress_color = "MODERATE", "🟡"
    else:
        stress_level, stress_color = "STABLE", "🟢"
        
    trend_word = "warming" if temp_slope > 0.05 else ("cooling" if temp_slope < -0.05 else "thermally stable")
    wettest_month = monthly["Rainfall_mm"].idxmax()
    wettest_val = monthly["Rainfall_mm"].max()
    
    insights = [
        {
            "title": "Temperature Trajectory",
            "body": f"{location_name} exhibits a **{trend_word}** rate of **{temp_slope:+.2f}°C/year**. Peak recorded temperature hit **{df['Temp_Max'].max():.1f}°C** (feels like **{df['Feels_Like_Max'].max():.1f}°C** with humidity)."
        },
        {
            "title": "Rainfall & Monsoon Concentration",
            "body": f"Cumulative precipitation reached **{df['Rainfall_mm'].sum():.1f} mm** over **{len(df[df['Rainfall_mm'] > 1.0])} rainy days**. The wettest month was **{wettest_month}** with **{wettest_val:.1f} mm**."
        },
        {
            "title": "Unusual Weather & Solar Profile",
            "body": f"Detected **{len(heat_anomalies)} heat spikes** (>{temp_thresh:.1f}°C) and **{len(rain_anomalies)} heavy rain surges** (>{rain_thresh:.1f} mm/day). Mean solar irradiance is **{df['Solar_kWh_m2'].mean():.2f} kWh/m²/day**."
        }
    ]
    
    return {
        "df": df,
        "source": source,
        "monthly": monthly,
        "avg_temp": df["Temp_Avg"].mean(),
        "temp_delta_30d": temp_delta_30d,
        "max_temp": df["Temp_Max"].max(),
        "max_feels_like": df["Feels_Like_Max"].max(),
        "total_rain": df["Rainfall_mm"].sum(),
        "avg_humidity": df["Humidity_pct"].mean(),
        "humidity_delta_30d": humidity_delta_30d,
        "anomaly_count": len(all_anomalies),
        "all_anomalies": all_anomalies,
        "stress_level": stress_level,
        "stress_color": stress_color,
        "insights": insights
    }