import streamlit as st
import requests
import time
from datetime import datetime
import pytz
import json

# ============================= CONFIG =============================
API_KEY = st.secrets.get("WEATHER_API_KEY", "50e0ace4ca4444e68c812956251011")
LAT_LON = "25.993217,-97.172555"
UPDATE_INTERVAL = 60  # seconds

# ========================= PAGE CONFIG =========================
st.set_page_config(page_title="Starbase Weather", layout="centered")
st.title("Starbase Live Weather")
st.markdown("**Location:** Starbase, TX (25.993217, -97.172555)")

# ====================== CACHED API CALL ======================
@st.cache_data(ttl=UPDATE_INTERVAL, show_spinner=False)
def get_weather_data():
    url = "http://api.weatherapi.com/v1/astronomy.json"
    params = {"key": API_KEY, "q": LAT_LON}
    try:
        astro = requests.get(url, params=params, timeout=10).json()
        current_url = "http://api.weatherapi.com/v1/current.json"
        current_params = {"key": API_KEY, "q": LAT_LON, "aqi": "yes"}
        current = requests.get(current_url, params=current_params, timeout=10).json()
        return {**current, "astronomy": astro["astronomy"]["astro"]}
    except Exception as e:
        st.error(f"API Error: {e}")
        return None

# ====================== SESSION STATE =======================
if "last_update" not in st.session_state:
    st.session_state.last_update = time.time()

now = time.time()
elapsed = now - st.session_state.last_update

# Refresh only every 60 seconds
if elapsed >= UPDATE_INTERVAL:
    st.session_state.last_update = now
    st.cache_data.clear()

# ====================== FETCH DATA =========================
data = get_weather_data()
placeholder = st.empty()

if not data:
    with placeholder.container():
        st.warning("Waiting for weather data...")
    st.stop()

current = data["current"]
location = data["location"]
astro = data["astronomy"]

# ====================== TIME HANDLING =======================
utc_now = datetime.now(pytz.UTC)
starbase_tz = pytz.timezone("America/Chicago")
starbase_now = utc_now.astimezone(starbase_tz)

# Parse sunrise/sunset
sunrise_str = astro["sunrise"]  # e.g., "07:15 AM"
sunset_str = astro["sunset"]    # e.g., "06:30 PM"
sunrise_dt = starbase_tz.localize(datetime.strptime(f"{starbase_now.date()} {sunrise_str}", "%Y-%m-%d %I:%M %p"))
sunset_dt = starbase_tz.localize(datetime.strptime(f"{starbase_now.date()} {sunset_str}", "%Y-%m-%d %I:%M %p"))

# Day/Night logic
is_daytime = sunrise_dt <= starbase_now <= sunset_dt
day_status = "daytime" if is_daytime else "nighttime"
icon = "Sun" if is_daytime else "Moon"

# Air Quality
epa_index = current["air_quality"]["us-epa-index"]
if epa_index <= 2:
    aq, color = "Good", "green"
elif epa_index <= 4:
    aq, color = "Moderate", "orange"
else:
    aq, color = "Unhealthy", "red"

# ====================== AUTO THEME (Light/Dark) =======================
theme = "light" if is_daytime else "dark"
st.markdown(
    f"""
    <style>
    .stApp {{ 
        background-color: {'#ffffff' if is_daytime else '#1e1e1e'};
        color: {'#000000' if is_daytime else '#ffffff'};
    }}
    .stMetric > div {{ 
        color: {'#000' if is_daytime else '#fff'} !important;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# ====================== LIVE COUNTDOWN (JS) =======================
seconds_left = int(UPDATE_INTERVAL - (now - st.session_state.last_update))
js = f"""
<script>
let secs = {seconds_left};
const counter = parent.document.getElementById('countdown');
const interval = setInterval(() => {{
    if (secs <= 0) {{
        clearInterval(interval);
        location.reload();
    }}
    counter.innerText = secs + (secs === 1 ? ' sec' : ' secs');
    secs--;
}}, 1000);
</script>
"""
countdown_placeholder = st.empty()

# ====================== DISPLAY ============================
with placeholder.container():
    # Header with icon
    st.markdown(f"### {icon} **{day_status.capitalize()} at Starbase**")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Temperature", f"{current['temp_c']}°C", f"{current['temp_f']}°F")
        st.metric("Feels Like", f"{current['feelslike_c']}°C", f"{current['feelslike_f']}°F")
    with col2:
        st.metric("Humidity", f"{current['humidity']}%")
        st.metric("Wind", f"{current['wind_kph']} kph", f"{current['wind_mph']} mph")

    st.markdown(f"### Air Quality: **{aq}** (EPA Index: {epa_index})")
    st.markdown(f"**Wind Direction:** {current['wind_dir']}")
    st.markdown(f"**Precipitation:** {current['precip_mm']} mm ({current['precip_in']} in)")
    st.markdown(f"**Visibility:** {current['vis_km']} km ({current['vis_miles']} mi)")

    # Sunrise / Sunset
    st.markdown(f"""
    **Sunrise:** `{sunrise_dt.strftime('%H:%M')}`  
    **Sunset:** `{sunset_dt.strftime('%H:%M')}`
    """)

    # Live time + countdown
    st.info(f"""
    **Starbase Time:** `{starbase_now.strftime('%Y-%m-%d %H:%M:%S')}`  
    **Data from:** `{location['localtime']}`  
    **Next update in:** <span id="countdown">{seconds_left} secs</span>
    """, unsafe_allow_html=True)

    # Inject JS
    countdown_placeholder.markdown(js, unsafe_allow_html=True)

    st.caption(f"Last refresh: {datetime.fromtimestamp(st.session_state.last_update):%H:%M:%S}")
