import streamlit as st
import requests
import time
from datetime import datetime, timedelta
import pytz
from streamlit.components.v1 import html

# ---------- CONFIG ----------
API_KEY = st.secrets.get("WEATHER_API_KEY", "50e0ace4ca4444e68c812956251011")
LAT_LON = "25.993217,-97.172555"
UPDATE_INTERVAL = 60  # seconds

# ---------- PAGE ----------
st.set_page_config(
    page_title="Starbase Live Weather",
    page_icon="https://spacex.com/favicon.ico",
    layout="centered"
)

# ---------- CACHED API ----------
@st.cache_data(ttl=UPDATE_INTERVAL, show_spinner="Fetching latest weather...")
def fetch_all():
    try:
        cur = requests.get(
            "http://api.weatherapi.com/v1/current.json",
            params={"key": API_KEY, "q": LAT_LON, "aqi": "yes"},
            timeout=10
        )
        cur.raise_for_status()
        cur = cur.json()

        astro = requests.get(
            "http://api.weatherapi.com/v1/astronomy.json",
            params={"key": API_KEY, "q": LAT_LON},
            timeout=10
        )
        astro.raise_for_status()
        astro = astro.json()["astronomy"]["astro"]

        cur["astronomy"] = astro
        return cur

    except requests.exceptions.RequestException as e:
        st.error(f"Weather API error: {str(e)}")
        return None
    except (KeyError, ValueError, TypeError):
        st.error("Invalid response from weather service.")
        return None

# ---------- SESSION STATE ----------
if "last_update" not in st.session_state:
    st.session_state.last_update = time.time()

now = time.time()
if now - st.session_state.last_update >= UPDATE_INTERVAL:
    st.session_state.last_update = now
    st.cache_data.clear()

# ---------- DATA ----------
data = fetch_all()
if not data:
    st.stop()

current = data["current"]
location = data["location"]
astro = data["astronomy"]

# ---------- TIME ----------
utc_now = datetime.now(pytz.UTC)
tz = pytz.timezone("America/Chicago")
now_local = utc_now.astimezone(tz)

def parse_time(t):
    time_obj = datetime.strptime(t, "%I:%M %p").time()
    candidate = tz.localize(datetime.combine(now_local.date(), time_obj))
    if candidate < now_local:
        candidate += timedelta(days=1)
    return candidate

sunrise = parse_time(astro["sunrise"])
sunset = parse_time(astro["sunset"])
is_day = sunrise <= now_local <= sunset

# ---------- AUTO THEME ----------
text_color = "#ffffff" if not is_day else "#000000"
bg_color = "#fafafa" if is_day else "#1e1e1e"

st.markdown(f"""
<style>
    .stApp {{ background: {bg_color}; color: {text_color}; }}
    .stMetric > div, h1, h2, h3, p, div, span, .stMarkdown, .stCaption {{ color: {text_color} !important; }}
    .stMetric label {{ color: {text_color} !important; }}
</style>
""", unsafe_allow_html=True)

# ---------- LIVE CLOCK + COUNTDOWN ----------
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

  function updateClock() {{
    const now = new Date();
    const formatter = new Intl.DateTimeFormat('en-US', {{
      timeZone: 'America/Chicago',
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
      hour12: false
    }});
    const parts = formatter.formatToParts(now);
    const obj = parts.reduce((acc, part) => {{ acc[part.type] = part.value; return acc; }}, {{}});
    const fmt = `${{obj.year}}-${{obj.month}}-${{obj.day}} ${{obj.hour}}:${{obj.minute}}:${{obj.second}}`;
    clockEl.innerText = fmt;

    const elapsed = Math.floor((Date.now() / 1000) - startTime);
    const left = {UPDATE_INTERVAL} - (elapsed % {UPDATE_INTERVAL});
    countEl.innerText = `Next update in ${{left}} ${{left === 1 ? 'sec' : 'secs'}}`;
    
    if (left <= 0) location.reload();
  }}

  setInterval(updateClock, 1000);
  updateClock();
</script>
"""
html(clock_html, height=100)

# ---------- TITLE ----------
st.title("Starbase Live Weather")
st.markdown("**Location:** Starbase, TX (25.993217, -97.172555)")

# ---------- WEATHER CONDITION ----------
condition = current["condition"]["text"]
icon_url = f"https:{current['condition']['icon']}"
st.markdown(f"**{condition}**")
st.image(icon_url, width=80)

# ---------- ROW 1: TEMP + WIND ----------
c1, c2 = st.columns(2)
with c1:
    st.metric("Temperature", f"{current['temp_c']}°C", f"{current['temp_f']}°F")
    st.metric("Feels Like", f"{current['feelslike_c']}°C", f"{current['feelslike_f']}°F")
with c2:
    st.metric("Humidity", f"{current['humidity']}%")
    st.metric("Wind", f"{current['wind_kph']} kph", f"{current['wind_mph']} mph")

# ---------- ROW 2: PRECIP + VIS ----------
c3, c4 = st.columns(2)
with c3:
    st.metric("Precipitation", f"{current['precip_mm']} mm", f"{current['precip_in']} in")
    st.metric("UV Index", current["uv"])
with c4:
    st.metric("Visibility", f"{current['vis_km']} km", f"{current['vis_miles']} mi")
    st.metric("Cloud Cover", f"{current['cloud']}%")

# ---------- ROW 3: AIR QUALITY + LAUNCH CHECK ----------
c5, c6 = st.columns(2)

# Air Quality
epa = current["air_quality"]["us-epa-index"]
aq = "Good" if epa <= 2 else "Moderate" if epa <= 4 else "Unhealthy"
aq_color = "green" if epa <= 2 else "orange" if epa <= 4 else "red"
with c5:
    st.markdown(f"### Air Quality")
    st.markdown(f"<span style='font-size:1.2em; color:{aq_color};'>**{aq}**</span> (EPA {epa})", unsafe_allow_html=True)

# Launch-Safe Check
wind_kph = current["wind_kph"]
gust_kph = current.get("gust_kph", wind_kph * 1.5)
precip_rate = current["precip_mm"]
vis_km = current["vis_km"]
condition_lower = current["condition"]["text"].lower()

has_thunder = any(k in condition_lower for k in ("thunder", "storm", "lightning"))
heavy_rain = precip_rate > 5.0
low_vis = vis_km < 5.0
wind_excess = wind_kph > 30 or gust_kph > 45

launch_safe = not (has_thunder or heavy_rain or low_vis or wind_excess)
safety_icon = "SAFE" if launch_safe else "ABORT"
safety_color = "green" if launch_safe else "red"

issues = []
if has_thunder:   issues.append("Thunderstorm")
if heavy_rain:    issues.append(f"Rain {precip_rate:.1f} mm/h")
if low_vis:       issues.append(f"Vis {vis_km} km")
if wind_excess:   issues.append(f"Wind {wind_kph}/{gust_kph:.1f} kph")

issue_text = " • ".join(issues) if issues else "Clear"

with c6:
    st.markdown(f"### Launch Check")
    st.markdown(
        f"<span style='font-size:1.2em; color:{safety_color};'>**{safety_icon}**</span><br>"
        f"<small>{issue_text}</small>",
        unsafe_allow_html=True
    )

# ---------- SUNRISE / SUNSET ----------
st.markdown(f"**Sunrise:** `{sunrise:%H:%M}` **Sunset:** `{sunset:%H:%M}`")

# ---------- WIND DIRECTION ----------
st.markdown(f"**Wind Direction:** {current['wind_dir']}")

# ---------- FOOTER ----------
st.markdown(f"**Data from:** `{location['localtime']}`")
st.caption(f"Last refresh: {datetime.fromtimestamp(st.session_state.last_update):%H:%M:%S} CST/CDT")
