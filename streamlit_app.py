# streamlit_app.py
import streamlit as st
import requests
import time
from datetime import datetime, timedelta
import pytz

# ============================= CONFIG =============================
API_KEY = "50e0ace4ca4444e68c812956251011"          # Use st.secrets in production
LAT_LON = "25.993217,-97.172555"
UPDATE_INTERVAL = 60                               # seconds (weather refresh)

# ========================= PAGE CONFIG =========================
st.set_page_config(page_title="Starbase Weather", layout="centered")
st.title("Starbase Live Weather")
st.markdown("**Location:** Starbase, TX (25.993217, -97.172555)")

# ====================== CACHED API CALL ======================
@st.cache_data(ttl=UPDATE_INTERVAL, show_spinner="Updating weather...")
def get_weather_data():
    url = "http://api.weatherapi.com/v1/current.json"
    params = {"key": API_KEY, "q": LAT_LON, "aqi": "yes"}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Weather API error: {e}")
        return None

# ========================= SESSION STATE =======================
if "start_time" not in st.session_state:
    st.session_state.start_time = time.time()
if "last_weather_update" not in st.session_state:
    st.session_state.last_weather_update = st.session_state.start_time

# ====================== AUTO REFRESH LOGIC ===================
now = time.time()
elapsed_since_update = now - st.session_state.last_weather_update

# Refresh weather every UPDATE_INTERVAL seconds
if elapsed_since_update >= UPDATE_INTERVAL:
    st.session_state.last_weather_update = now
    st.cache_data.clear()          # Force fresh API call
    st.rerun()

# Trigger a rerun **every second** to update the live counter
time.sleep(1)
st.rerun()

# ====================== FETCH WEATHER =========================
weather_data = get_weather_data()
placeholder = st.empty()

if not weather_data:
    with placeholder.container():
        st.warning("Waiting for weather data...")
    st.stop()

# ====================== TIME HANDLING =========================
current = weather_data["current"]
location = weather_data["location"]

# Starbase local time (America/Chicago = CST/CDT)
utc_now = datetime.now(pytz.UTC)
starbase_tz = pytz.timezone("America/Chicago")
starbase_now = utc_now.astimezone(starbase_tz)

# API-provided localtime (make it timezone-aware)
api_local_str = location["localtime"]
api_local_dt = datetime.strptime(api_local_str, "%Y-%m-%d %H:%M")
api_local_dt = starbase_tz.localize(api_local_dt)

# Day / Night
day_status = "daytime" if current["is_day"] == 1 else "nighttime"

# Air Quality
epa_index = current["air_quality"]["us-epa-index"]
if epa_index <= 2:
    aq, color = "Good", "🟢"
elif epa_index <= 4:
    aq, color = "Moderate", "🟡"
else:
    aq, color = "Unhealthy", "🔴"

# ====================== DISPLAY ==============================
with placeholder.container():
    # ---- Metrics Row ----
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Temperature", f"{current['temp_c']}°C", f"{current['temp_f']}°F")
        st.metric("Feels Like", f"{current['feelslike_c']}°C", f"{current['feelslike_f']}°F")
    with col2:
        st.metric("Humidity", f"{current['humidity']}%")
        st.metric("Wind", f"{current['wind_kph']} kph", f"{current['wind_mph']} mph")

    # ---- Main Info ----
    st.markdown(f"### {color} **Air Quality:** {aq} (EPA Index: {epa_index})")
    st.markdown(f"**Wind Direction:** {current['wind_dir']}")
    st.markdown(f"**Precipitation:** {current['precip_mm']} mm ({current['precip_in']} in)")
    st.markdown(f"**Visibility:** {current['vis_km']} km ({current['vis_miles']} mi)")

    # ---- Live Time & Counter ----
    secs_left = int(UPDATE_INTERVAL - (now - st.session_state.last_weather_update))
    st.info(f"""
    **Starbase Time:** {starbase_now.strftime('%m/%d/%Y %H:%M:%S')} ({starbase_tz})  
    **Currently:** {day_status}  
    **Data from:** {api_local_dt.strftime('%H:%M')}  
    **Next weather update in:** **{secs_left}** second{'s' if secs_left != 1 else ''}
    """)

    # Optional: show raw update timestamp
    st.caption(f"Last API fetch: {datetime.fromtimestamp(st.session_state.last_weather_update).strftime('%H:%M:%S')}")
