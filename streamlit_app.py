# --------------------------------------------------------------
#  Starbase Live Weather – CLOCK ON TOP + EVERYTHING WORKING
# --------------------------------------------------------------
import streamlit as st
import requests
import time
from datetime import datetime
import pytz
from streamlit.components.v1 import html

# ---------- CONFIG ----------
API_KEY = st.secrets.get("WEATHER_API_KEY", "50e0ace4ca4444e68c812956251011")
LAT_LON = "25.993217,-97.172555"
UPDATE_INTERVAL = 60

# ---------- PAGE ----------
st.set_page_config(
    page_title="Starbase Weather",
    page_icon="https://spacex.com/favicon.ico",
    layout="centered"
)

# ---------- CACHED API ----------
@st.cache_data(ttl=UPDATE_INTERVAL, show_spinner=False)
def fetch_all():
    cur = requests.get(
        "http://api.weatherapi.com/v1/current.json",
        params={"key": API_KEY, "q": LAT_LON, "aqi": "yes"},
        timeout=10
    ).json()
    astro = requests.get(
        "http://api.weatherapi.com/v1/astronomy.json",
        params={"key": API_KEY, "q": LAT_LON},
        timeout=10
    ).json()["astronomy"]["astro"]
    cur["astronomy"] = astro
    return cur

# ---------- SESSION ----------
if "last_update" not in st.session_state:
    st.session_state.last_update = time.time()

now = time.time()
if now - st.session_state.last_update >= UPDATE_INTERVAL:
    st.session_state.last_update = now
    st.cache_data.clear()

# ---------- DATA ----------
data = fetch_all()
if not data:
    st.warning("Waiting for data…")
    st.stop()

current = data["current"]
location = data["location"]
astro = data["astronomy"]

# ---------- TIME ----------
utc_now = datetime.now(pytz.UTC)
tz = pytz.timezone("America/Chicago")
now_local = utc_now.astimezone(tz)

def parse_time(t):
    return tz.localize(datetime.strptime(f"{now_local.date()} {t}", "%Y-%m-%d %I:%M %p"))

sunrise = parse_time(astro["sunrise"])
sunset  = parse_time(astro["sunset"])
is_day = sunrise <= now_local <= sunset
icon = "Sun" if is_day else "Moon"

# ---------- AIR QUALITY ----------
epa = current["air_quality"]["us-epa-index"]
aq = "Good" if epa <= 2 else "Moderate" if epa <= 4 else "Unhealthy"

# ---------- AUTO THEME ----------
text_color = "#ffffff" if not is_day else "#000000"
bg_color   = "#fafafa" if is_day else "#1e1e1e"

st.markdown(f"""
<style>
    .stApp {{ background: {bg_color}; color: {text_color}; }}
    .stMetric > div, h1, h2, h3, p, div, span, .stMarkdown {{ color: {text_color} !important; }}
</style>
""", unsafe_allow_html=True)

# ---------- LIVE CLOCK + COUNTDOWN (ON TOP) ----------
secs_left = int(UPDATE_INTERVAL - (now - st.session_state.last_update))

clock_html = f"""
<div style="text-align: center; padding: 10px; font-family: monospace;">
  <div id="starbase-clock" style="font-size: 1.8em; font-weight: bold; color: {text_color};">
    {now_local:%Y-%m-%d %H:%M:%S}
  </div>
  <div id="countdown" style="font-size: 1em; color: {text_color}; margin-top: 4px;">
    Next update in {secs_left} secs
  </div>
</div>
<script>
  const startTime = {int(time.time())};
  const clockEl = document.getElementById('starbase-clock');
  const countEl = document.getElementById('countdown');
  setInterval(() => {
    const now = new Date();
    const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
    const starbase = new Date(utc - 21600000);  // CST = UTC-6
    const fmt = starbase.toISOString().slice(0,19).replace('T', ' ');
    clockEl.innerText = fmt;

    const elapsed = Math.floor((Date.now()/1000) - startTime);
    const left = {UPDATE_INTERVAL} - (elapsed % {UPDATE_INTERVAL});
    countEl.innerText = `Next update in ${{left}} ${{left === 1 ? 'sec' : 'secs'}}`;

    if (left <= 0) location.reload();
  }, 1000);
</script>
"""

# ---------- TITLE + LOCATION ----------
st.title("Starbase Live Weather")
st.markdown("**Location:** Starbase, TX (25.993217, -97.172555)")

# ---------- DISPLAY CLOCK ON TOP ----------
html(clock_html, height=100)

# ---------- MAIN CONTENT ----------
st.markdown(f"### {icon} **{('Day' if is_day else 'Night')}time at Starbase**")

# Row 1
c1, c2 = st.columns(2)
with c1:
    st.metric("Temperature", f"{current['temp_c']}°C", f"{current['temp_f']}°F")
    st.metric("Feels Like", f"{current['feelslike_c']}°C", f"{current['feelslike_f']}°F")
with c2:
    st.metric("Humidity", f"{current['humidity']}%")
    st.metric("Wind", f"{current['wind_kph']} kph", f"{current['wind_mph']} mph")

# Row 2
c3, c4 = st.columns(2)
with c3:
    st.metric("Precipitation", f"{current['precip_mm']} mm", f"{current['precip_in']} in")
with c4:
    st.metric("Visibility", f"{current['vis_km']} km", f"{current['vis_miles']} mi")

st.markdown(f"### Air Quality: **{aq}** (EPA {epa})")
st.markdown(f"**Wind Dir:** {current['wind_dir']}")
st.markdown(f"**Sunrise:** `{sunrise:%H:%M}` **Sunset:** `{sunset:%H:%M}`")
st.markdown(f"**Data from:** `{location['localtime']}`")

st.caption(f"Last refresh: {datetime.fromtimestamp(st.session_state.last_update):%H:%M:%S}")
