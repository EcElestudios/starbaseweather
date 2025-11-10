# --------------------------------------------------------------
#  Starbase Live Weather – Streamlit (works with your env)
# --------------------------------------------------------------
import streamlit as st
import requests
import time
from datetime import datetime
import pytz

# ---------- CONFIG ----------
API_KEY = st.secrets.get("WEATHER_API_KEY", "50e0ace4ca4444e68c812956251011")
LAT_LON = "25.993217,-97.172555"
UPDATE_INTERVAL = 60          # seconds – weather refresh

# ---------- PAGE ----------
st.set_page_config(page_title="Starbase Weather", layout="centered")
st.title("Starbase Live Weather")
st.markdown("**Location:** Starbase, TX (25.993217, -97.172555)")

# ---------- CACHED API CALL ----------
@st.cache_data(ttl=UPDATE_INTERVAL, show_spinner=False)
def fetch_all():
    # 1. Current + AQI
    cur_url = "http://api.weatherapi.com/v1/current.json"
    cur_params = {"key": API_KEY, "q": LAT_LON, "aqi": "yes"}
    cur = requests.get(cur_url, params=cur_params, timeout=10).json()

    # 2. Astronomy (sunrise/sunset) – free endpoint
    astro_url = "http://api.weatherapi.com/v1/astronomy.json"
    astro_params = {"key": API_KEY, "q": LAT_LON}
    astro = requests.get(astro_url, params=astro_params, timeout=10).json()["astronomy"]["astro"]

    cur["astronomy"] = astro
    return cur

# ---------- SESSION STATE ----------
if "last_update" not in st.session_state:
    st.session_state.last_update = time.time()

now = time.time()
elapsed = now - st.session_state.last_update

# Refresh data only every UPDATE_INTERVAL
if elapsed >= UPDATE_INTERVAL:
    st.session_state.last_update = now
    st.cache_data.clear()          # forces a fresh call

# ---------- FETCH ----------
data = fetch_all()
placeholder = st.empty()

if not data:
    with placeholder.container():
        st.warning("Waiting for weather data…")
    st.stop()

current = data["current"]
location = data["location"]
astro = data["astronomy"]

# ---------- TIME HANDLING ----------
utc_now = datetime.now(pytz.UTC)
starbase_tz = pytz.timezone("America/Chicago")
starbase_now = utc_now.astimezone(starbase_tz)

# Sunrise / Sunset (parse “07:15 AM” style strings)
def parse_astro(t):
    return starbase_tz.localize(
        datetime.strptime(f"{starbase_now.date()} {t}", "%Y-%m-%d %I:%M %p")
    )
sunrise_dt = parse_astro(astro["sunrise"])
sunset_dt  = parse_astro(astro["sunset"])

is_day = sunrise_dt <= starbase_now <= sunset_dt
status = "daytime" if is_day else "nighttime"
icon   = "Sun" if is_day else "Moon"

# ---------- AIR QUALITY ----------
epa = current["air_quality"]["us-epa-index"]
if epa <= 2:
    aq, col = "Good", "green"
elif epa <= 4:
    aq, col = "Moderate", "orange"
else:
    aq, col = "Unhealthy", "red"

# ---------- AUTO THEME ----------
theme_css = f"""
<style>
    .stApp {{ background: {'#fafafa' if is_day else '#1e1e1e'}; 
              color: {'#000' if is_day else '#fff'}; }}
    .stMetric > div {{ color: {'#000' if is_day else '#fff'} !important; }}
</style>
"""
st.markdown(theme_css, unsafe_allow_html=True)

# ---------- LIVE COUNTDOWN (JS) ----------
secs_left = int(UPDATE_INTERVAL - (now - st.session_state.last_update))
js = f"""
<script>
let s = {secs_left};
const el = parent.document.getElementById('cnt');
const iv = setInterval(() => {{
    if (s <= 0) {{ clearInterval(iv); location.reload(); }}
    el.innerText = s + (s===1 ? ' sec' : ' secs');
    s--;
}}, 1000);
</script>
"""
countdown_ph = st.empty()

# ---------- DISPLAY ----------
with placeholder.container():
    st.markdown(f"### {icon} **{status.capitalize()} at Starbase**")

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Temperature", f"{current['temp_c']}°C", f"{current['temp_f']}°F")
        st.metric("Feels Like", f"{current['feelslike_c']}°C", f"{current['feelslike_f']}°F")
    with c2:
        st.metric("Humidity", f"{current['humidity']}%")
        st.metric("Wind", f"{current['wind_kph']} kph", f"{current['wind_mph']} mph")

    st.markdown(f"### Air Quality: **{aq}** (EPA {epa})")
    st.markdown(f"**Wind Dir:** {current['wind_dir']}")
    st.markdown(f"**Precip:** {current['precip_mm']} mm ({current['precip_in']} in)")
    st.markdown(f"**Visibility:** {current['vis_km']} km ({current['vis_miles']} mi)")

    st.markdown(f"**Sunrise:** `{sunrise_dt:%H:%M}` **Sunset:** `{sunset_dt:%H:%M}`")

    st.info(f"""
    **Starbase Time:** `{starbase_now:%Y-%m-%d %H:%M:%S}`  
    **Data from:** `{location['localtime']}`  
    **Next update in:** <span id="cnt">{secs_left} secs</span>
    """, unsafe_allow_html=True)

    countdown_ph.markdown(js, unsafe_allow_html=True)

    st.caption(f"Last refresh: {datetime.fromtimestamp(st.session_state.last_update):%H:%M:%S}")
