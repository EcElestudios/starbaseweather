# --------------------------------------------------------------
#  Starbase Live Weather – Auto Theme + Adaptive Text Color
# --------------------------------------------------------------
import streamlit as st
import requests
import time
from datetime import datetime
import pytz

# ---------- CONFIG ----------
API_KEY = st.secrets.get("WEATHER_API_KEY", "50e0ace4ca4444e68c812956251011")
LAT_LON = "25.993217,-97.172555"
UPDATE_INTERVAL = 60

# ---------- PAGE ----------
st.set_page_config(page_title="Starbase Weather", layout="centered")
st.title("Starbase Live Weather")
st.markdown("**Location:** Starbase, TX (25.993217, -97.172555)")

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
placeholder = st.empty()
if not data:
    with placeholder.container():
        st.warning("Waiting for data…")
    st.stop()

current = data["current"]
location = data["location"]
astro = data["astronomy"]

# ---------- TIME ----------
utc_now = datetime.now(pytz.UTC)
tz = pytz.timezone("America/Chicago")
now_local = utc_now.astimezone(tz)

def parse_time(t):  # "07:15 AM"
    return tz.localize(datetime.strptime(f"{now_local.date()} {t}", "%Y-%m-%d %I:%M %p"))

sunrise = parse_time(astro["sunrise"])
sunset  = parse_time(astro["sunset"])
is_day = sunrise <= now_local <= sunset
icon = "Sun" if is_day else "Moon"
mode = "light" if is_day else "dark"

# ---------- AIR QUALITY ----------
epa = current["air_quality"]["us-epa-index"]
aq = "Good" if epa <= 2 else "Moderate" if epa <= 4 else "Unhealthy"

# ---------- AUTO THEME + TEXT COLOR ----------
text_color = "#ffffff" if not is_day else "#000000"
bg_color   = "#fafafa" if is_day else "#1e1e1e"

st.markdown(f"""
<style>
    .stApp {{ background: {bg_color}; color: {text_color}; }}
    .stMetric > div {{ color: {text_color} !important; }}
    h1, h2, h3, h4, h5, h6, p, div, span {{ color: {text_color} !important; }}
    .stMarkdown {{ color: {text_color} !important; }}
</style>
""", unsafe_allow_html=True)

# ---------- COUNTDOWN JS ----------
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
    st.markdown(f"### {icon} **{('Day' if is_day else 'Night')}time at Starbase**")

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Temperature", f"{current['temp_c']}°C", f"{current['temp_f']}°F")
        st.metric("Feels Like", f"{current['feelslike_c']}°C", f"{current['feelslike_f']}°F")
    with c2:
        st.metric("Humidity", f"{current['humidity']}%")
        st.metric("Wind", f"{current['wind_kph']} kph", f"{current['wind_mph']} mph")

    st.markdown(f"### Air Quality: **{aq}** (EPA {epa})")
    st.markdown(f"**Wind:** {current['wind_dir']} **Precip:** {current['precip_mm']} mm **Vis:** {current['vis_km']} km")

    st.markdown(f"**Sunrise:** `{sunrise:%H:%M}` **Sunset:** `{sunset:%H:%M}`")

    # Use markdown for full HTML + styling
    st.markdown(f"""
    **Starbase Time:** `{now_local:%Y-%m-%d %H:%M:%S}`  
    **Data from:** `{location['localtime']}`  
    **Next update in:** <span id="cnt" style="font-weight:bold">{secs_left} secs</span>
    """, unsafe_allow_html=True)

    countdown_ph.markdown(js, unsafe_allow_html=True)

    st.caption(f"Last refresh: {datetime.fromtimestamp(st.session_state.last_update):%H:%M:%S}")
