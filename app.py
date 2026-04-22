import streamlit as st
import urllib.request
import xml.etree.ElementTree as ET
import json
import time
import threading
from collections import defaultdict

# ── Constants ──────────────────────────────────────────────────────────────────
DSN_URL   = "https://eyes.nasa.gov/dsn/data/dsn.xml"
ASTROS_URL = "http://api.open-notify.org/astros.json"
ISS_URL   = "https://api.wheretheiss.at/v1/satellites/25544"
LIGHT_SPEED = 299792.458
REFRESH_INTERVAL = 5

MISSION_NAMES = {
    "JNO": "Juno (Jupiter)", "VGR1": "Voyager 1", "VGR2": "Voyager 2",
    "VOY1": "Voyager 1", "VOY2": "Voyager 2",
    "MSL": "Curiosity Rover", "M20": "Perseverance Rover",
    "MAVEN": "MAVEN (Mars)", "MRO": "Mars Recon. Orbiter",
    "ODY": "Mars Odyssey", "TGO": "ExoMars TGO", "MEX": "Mars Express",
    "EMM": "Hope (UAE)", "ESCB": "EscaPADE", "KPLO": "Danuri (Korea)",
    "EM2": "Artemis II", "ORBT": "Lunar Recon. Orbiter", "CAPL": "CAPSTONE",
    "CAPS": "CAPSTONE", "PARK": "Parker Solar Probe", "SOLO": "Solar Orbiter",
    "BEPI": "BepiColombo", "JUICE": "JUICE (Jupiter)", "LUCY": "Lucy (Asteroids)",
    "PSY": "Psyche", "OSIRIS": "OSIRIS-REx", "ORX": "OSIRIS-REx",
    "JWST": "James Webb Telescope", "EUCL": "Euclid Telescope",
    "NEOWI": "NEOWISE", "DSCOV": "DSCOVR", "ACE": "Adv. Composition Explorer",
    "SOHO": "SOHO", "WIND": "WIND", "CHDR": "Chandra",
    "MMS1": "MMS-1", "MMS2": "MMS-2", "MMS3": "MMS-3", "MMS4": "MMS-4",
    "EURC": "Europa Clipper",
    "ISS":  "Intl. Space Station",
    "ISSLIVE": "Intl. Space Station",
    "TGS":  "Tiangong Station",
    "CSS":  "Tiangong Station",
}

# Maps spacecraft display name → crew-data key from astros.json
CREWED_VEHICLES = {
    "Intl. Space Station": "ISS",
    "Tiangong Station": "Tiangong",
}

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NASA DSN Live Monitor",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 !important; max-width: 100% !important; }
section[data-testid="stSidebar"] { display: none; }

.stApp {
    background-color: #04040f;
    color: #c8d8f0;
    font-family: 'Courier New', Courier, monospace;
}

/* ── Header ── */
.dsn-header {
    background: linear-gradient(135deg, #05061a 0%, #0a1535 60%, #05061a 100%);
    border-bottom: 2px solid #00d4ff;
    padding: 1.2rem 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.dsn-title {
    font-size: 1.5rem;
    font-weight: bold;
    color: #00d4ff;
    letter-spacing: 4px;
    text-transform: uppercase;
}
.dsn-subtitle {
    font-size: 0.68rem;
    color: #4a6a8a;
    letter-spacing: 3px;
    margin-top: 3px;
}
.dsn-right { text-align: right; }
.dsn-ts { font-size: 0.8rem; color: #6a8aaa; letter-spacing: 1px; }
.live-indicator {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    font-size: 0.75rem;
    color: #00ff88;
    letter-spacing: 2px;
    margin-bottom: 4px;
}
.live-dot {
    width: 9px; height: 9px;
    background: #00ff88;
    border-radius: 50%;
    animation: pulse 1.6s ease-in-out infinite;
}
@keyframes pulse {
    0%   { opacity: 1;   box-shadow: 0 0 0 0   #00ff8855; }
    50%  { opacity: 0.6; box-shadow: 0 0 0 7px transparent; }
    100% { opacity: 1;   box-shadow: 0 0 0 0   transparent; }
}

/* ── Humans in space section ── */
.humans-section {
    padding: 1rem 2rem;
    background: #050916;
    border-bottom: 1px solid #0e1e38;
}
.section-label {
    font-size: 0.62rem;
    color: #2a5070;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 0.75rem;
}
.craft-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 1rem;
}
.craft-card {
    background: linear-gradient(135deg, #07091c 0%, #0a1030 100%);
    border: 1px solid #162840;
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
}
.craft-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.65rem;
}
.craft-name {
    font-size: 0.9rem;
    font-weight: bold;
    color: #00d4ff;
    letter-spacing: 1px;
}
.craft-count {
    font-size: 0.7rem;
    color: #3a6a8a;
    letter-spacing: 1px;
}
.telem-row {
    display: flex;
    gap: 1.2rem;
    flex-wrap: wrap;
    margin-bottom: 0.65rem;
    padding-bottom: 0.65rem;
    border-bottom: 1px solid #101e30;
}
.telem-item {}
.telem-lbl {
    font-size: 0.57rem;
    color: #2a4a62;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 2px;
}
.telem-val {
    font-size: 0.8rem;
    color: #90b8d8;
}
.vis-day     { color: #ffcc44; }
.vis-eclipse { color: #6688ff; }
.vis-night   { color: #4466aa; }
.crew-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.2rem 0.5rem;
}
.crew-member {
    font-size: 0.74rem;
    color: #7a9ab8;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.crew-dot {
    display: inline-block;
    width: 6px; height: 6px;
    background: #00d4ff40;
    border-radius: 50%;
    margin-right: 5px;
    vertical-align: middle;
}

/* ── Metrics row ── */
.metrics-row {
    display: flex;
    gap: 1rem;
    padding: 1.25rem 2rem;
    background: #06071a;
    border-bottom: 1px solid #0e1e38;
}
.metric-card {
    flex: 1;
    background: linear-gradient(135deg, #090e22 0%, #0d1635 100%);
    border: 1px solid #162840;
    border-radius: 10px;
    padding: 0.9rem 1.4rem;
    text-align: center;
}
.metric-value {
    font-size: 1.9rem;
    font-weight: bold;
    color: #00d4ff;
    line-height: 1.1;
}
.metric-label {
    font-size: 0.62rem;
    color: #3a5a7a;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: 5px;
}

/* ── Stations ── */
.stations-wrapper { padding: 1.5rem 2rem 2rem 2rem; }
.station-block { margin-bottom: 2rem; }
.station-header {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    border-left: 4px solid #00d4ff;
    padding: 0.45rem 1rem;
    margin-bottom: 1rem;
    background: linear-gradient(90deg, #00d4ff0d 0%, transparent 100%);
}
.station-name {
    font-size: 0.92rem;
    font-weight: bold;
    color: #00d4ff;
    letter-spacing: 3px;
    text-transform: uppercase;
}
.station-count { font-size: 0.7rem; color: #3a5a7a; letter-spacing: 1px; }

/* ── Dish cards ── */
.dish-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
    gap: 1rem;
}
.dish-card {
    background: linear-gradient(145deg, #070c1c 0%, #0a1228 100%);
    border: 1px solid #12243a;
    border-radius: 10px;
    padding: 1rem 1.1rem;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.dish-card:hover {
    border-color: #00d4ff50;
    box-shadow: 0 0 22px #00d4ff12;
}
.dish-badge {
    display: inline-block;
    background: #00d4ff18;
    border: 1px solid #00d4ff35;
    border-radius: 5px;
    padding: 2px 11px;
    font-size: 0.82rem;
    font-weight: bold;
    color: #00d4ff;
    margin-bottom: 0.8rem;
    letter-spacing: 1px;
}

/* ── Spacecraft row ── */
.sc-row {
    padding: 0.7rem 0 0 0;
    border-top: 1px solid #101e30;
}
.sc-row:first-child { border-top: none; padding-top: 0; }
.sc-name {
    font-size: 0.9rem;
    font-weight: bold;
    color: #f0c030;
    margin-bottom: 0.55rem;
    letter-spacing: 0.5px;
}
.sc-name-crewed { color: #60e0ff; }
.sc-data {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.35rem 0.5rem;
}
.sc-lbl {
    font-size: 0.58rem;
    color: #3a5570;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 1px;
}
.sc-val { font-size: 0.8rem; color: #a8c0d8; white-space: nowrap; }

/* ── Crew aboard in dish card ── */
.sc-crew {
    margin-top: 0.5rem;
    padding-top: 0.45rem;
    border-top: 1px dashed #0e2035;
}
.sc-crew-lbl {
    font-size: 0.57rem;
    color: #2a5070;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 0.3rem;
}
.sc-crew-names {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
}
.crew-pill {
    font-size: 0.68rem;
    color: #60a8c8;
    background: #00d4ff10;
    border: 1px solid #00d4ff20;
    border-radius: 3px;
    padding: 1px 7px;
    white-space: nowrap;
}

/* ── Signal / band ── */
.sig-strong { color: #00ff88; }
.sig-medium { color: #ffcc00; }
.sig-weak   { color: #ff5555; }
.sig-none   { color: #2a4a62; }
.band {
    display: inline-block;
    padding: 0px 6px;
    border-radius: 3px;
    font-size: 0.68rem;
    font-weight: bold;
    margin-right: 3px;
    vertical-align: middle;
}
.band-S { background: #0a2535; color: #00bbdd; border: 1px solid #00bbdd30; }
.band-X { background: #1e0a2e; color: #bb00ee; border: 1px solid #bb00ee30; }
.band-K { background: #2e0a0a; color: #ff6600; border: 1px solid #ff660030; }
.band-none { background: #0d1520; color: #2a4055; border: 1px solid #1a2535; }

/* ── Idle / maintenance view ── */
.msg-waiting {
    text-align: center;
    padding: 2rem 2rem 1rem 2rem;
    color: #3a6a82;
    font-size: 0.85rem;
    letter-spacing: 3px;
    text-transform: uppercase;
}
.idle-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 0.6rem;
    margin-top: 0.6rem;
}
.idle-card {
    background: #07090f;
    border: 1px solid #0e1a28;
    border-radius: 8px;
    padding: 0.6rem 0.9rem;
    display: flex;
    align-items: center;
    gap: 0.6rem;
}
.idle-dish { font-size: 0.8rem; color: #2a5a72; font-weight: bold; min-width: 52px; }
.idle-activity { font-size: 0.72rem; color: #244050; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* ── Footer ── */
.dsn-footer {
    padding: 0.9rem 2rem;
    border-top: 1px solid #0e1e30;
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: #2a4a62;
    font-size: 0.7rem;
    letter-spacing: 1px;
}
.footer-legend { display: flex; gap: 1.5rem; }

/* ── Error ── */
.msg-error {
    background: #1a0808;
    border: 1px solid #8b2222;
    border-radius: 8px;
    padding: 1rem 1.5rem;
    color: #ff6666;
    margin: 1.5rem 2rem;
    font-size: 0.85rem;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────
def _pos_float(s):
    """Return float if s parses to a positive number, else None. Rejects -1 sentinel."""
    try:
        v = float(s)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def _fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read())


def sig_class(dpow_str: str) -> str:
    if dpow_str == "---":
        return "sig-none"
    try:
        dbm = float(dpow_str.replace(" dBm", ""))
        if dbm > -120:   return "sig-strong"
        elif dbm > -140: return "sig-medium"
        return "sig-weak"
    except Exception:
        return "sig-none"


def band_html(band: str) -> str:
    b = band.strip().upper()
    cls = f"band-{b}" if b in ("S", "X", "K") else "band-none"
    label = b if b in ("S", "X", "K") else "—"
    return f'<span class="band {cls}">{label}</span>'


def sc_row_html(r: dict, crew: list | None = None) -> str:
    sig_cls = sig_class(r["dpow"])
    is_crewed = crew is not None and len(crew) > 0
    name_cls = "sc-name sc-name-crewed" if is_crewed else "sc-name"

    crew_html = ""
    if is_crewed:
        pills = "".join(f'<span class="crew-pill">{n}</span>' for n in crew)
        crew_html = f"""
  <div class="sc-crew">
    <div class="sc-crew-lbl">👨‍🚀 Crew aboard</div>
    <div class="sc-crew-names">{pills}</div>
  </div>"""

    return f"""
<div class="sc-row">
  <div class="{name_cls}">{r['sc']}</div>
  <div class="sc-data">
    <div class="sc-item">
      <div class="sc-lbl">Uplink</div>
      <div class="sc-val">{band_html(r['uband'])} {r['upow']}</div>
    </div>
    <div class="sc-item">
      <div class="sc-lbl">Downlink</div>
      <div class="sc-val">{band_html(r['dband'])} <span class="{sig_cls}">{r['dpow']}</span></div>
    </div>
    <div class="sc-item">
      <div class="sc-lbl">Data Rate</div>
      <div class="sc-val">{r['drate']}</div>
    </div>
    <div class="sc-item">
      <div class="sc-lbl">Distance</div>
      <div class="sc-val">{r['dist']}</div>
    </div>
    <div class="sc-item">
      <div class="sc-lbl">Light Trip</div>
      <div class="sc-val">{r['rtlt']}</div>
    </div>
  </div>{crew_html}
</div>"""


def dish_card_html(dish_name: str, targets: list, humans: dict) -> str:
    rows_html = ""
    for r in targets:
        crew_key = CREWED_VEHICLES.get(r["sc"])
        crew = humans.get(crew_key) if crew_key else None
        rows_html += sc_row_html(r, crew)
    return f"""
<div class="dish-card">
  <div class="dish-badge">📡 {dish_name}</div>
  {rows_html}
</div>"""


# ── Data fetching ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=REFRESH_INTERVAL - 1)
def fetch_dsn_data():
    try:
        req = urllib.request.Request(DSN_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            root = ET.fromstring(resp.read())

        rows = []
        all_dishes = defaultdict(list)
        current_station = "Unknown"
        dsn_ts = root.findtext("timestamp") or "—"

        for child in root:
            if child.tag == "station":
                current_station = child.get("friendlyName", "Unknown")

            elif child.tag == "dish":
                dish_name = child.get("name", "??")
                activity  = child.get("activity", "Idle")
                all_dishes[current_station].append({"dish": dish_name, "activity": activity})

                down_signals = {
                    sig.get("spacecraft", "").upper(): {
                        "p": sig.get("power"), "rate": sig.get("dataRate"),
                        "band": sig.get("band"),
                    }
                    for sig in child.findall("downSignal") if sig.get("spacecraft")
                }
                up_signals = {
                    sig.get("spacecraft", "").upper(): {
                        "p": sig.get("power"), "band": sig.get("band"),
                    }
                    for sig in child.findall("upSignal") if sig.get("spacecraft")
                }

                for target in child.findall("target"):
                    code = (target.get("name") or "").upper()
                    if not code or code in ("DSN", "DSS", "NONE", "---"):
                        continue

                    full_name = MISSION_NAMES.get(code, code)
                    dist_str = rtlt_str = "---"

                    km   = (_pos_float(target.get("uplegRange"))
                            or _pos_float(target.get("downlegRange")))
                    rtlt = _pos_float(target.get("rtlt"))

                    if rtlt is not None:
                        rtlt_str = (f"{rtlt:.1f} s" if rtlt < 60
                                    else f"{rtlt / 60:,.2f} min")
                    if km is None and rtlt is not None:
                        km = (rtlt / 2) * LIGHT_SPEED
                    if km is not None:
                        dist_str = (f"{km / 1e3:,.0f}K km" if km < 999_999
                                    else f"{km / 1e6:,.2f}M km")

                    dsig   = down_signals.get(code, {})
                    dp_val = dsig.get("p")
                    dr_val = dsig.get("rate")
                    dband  = dsig.get("band") or "---"

                    dp_str = drate_str = "---"
                    if dp_val and dp_val != "none":
                        dp_str = f"{dp_val} dBm"
                    if dr_val and dr_val != "none":
                        try:
                            rate_f = float(dr_val)
                            drate_str = (f"{rate_f / 1e6:,.3f} Mb/s" if rate_f >= 1e6
                                         else f"{rate_f / 1e3:,.2f} kb/s")
                        except Exception:
                            pass

                    usig   = up_signals.get(code, {})
                    up_val = usig.get("p")
                    uband  = usig.get("band") or "---"
                    up_str = f"{up_val} kW" if (up_val and up_val != "none") else "---"

                    rows.append({
                        "loc": current_station, "dish": dish_name, "sc": full_name,
                        "dpow": dp_str, "drate": drate_str, "dist": dist_str,
                        "rtlt": rtlt_str, "upow": up_str, "dband": dband, "uband": uband,
                    })

        return rows, dict(all_dishes), dsn_ts
    except Exception as exc:
        return None, {}, str(exc)


# ── Background humans fetch ────────────────────────────────────────────────────
# Module-level state persists across Streamlit reruns; the thread refreshes it
# every HUMANS_TTL seconds without ever blocking the render path.
HUMANS_TTL = 30
_humans_state: dict = {"humans": {}, "iss_telem": {}, "ts": 0.0, "fetching": False}
_humans_lock = threading.Lock()


def _do_fetch_humans():
    by_craft: dict = {}
    iss_telem: dict = {}
    try:
        raw = _fetch_json(ASTROS_URL)
        tmp: dict = defaultdict(list)
        for p in raw.get("people", []):
            tmp[p["craft"]].append(p["name"])
        by_craft = dict(tmp)
    except Exception:
        pass
    try:
        iss_telem = _fetch_json(ISS_URL)
    except Exception:
        pass
    return by_craft, iss_telem


def _humans_bg_worker():
    humans, iss_telem = _do_fetch_humans()
    with _humans_lock:
        _humans_state["humans"]   = humans
        _humans_state["iss_telem"] = iss_telem
        _humans_state["ts"]       = time.time()
        _humans_state["fetching"] = False


def get_humans():
    """Return cached humans data immediately; kick off a background refresh if stale."""
    with _humans_lock:
        age      = time.time() - _humans_state["ts"]
        fetching = _humans_state["fetching"]
        humans   = _humans_state["humans"]
        telem    = _humans_state["iss_telem"]

    if age > HUMANS_TTL and not fetching:
        with _humans_lock:
            _humans_state["fetching"] = True
        threading.Thread(target=_humans_bg_worker, daemon=True).start()

    return humans, telem


# ── Build humans-in-space HTML ─────────────────────────────────────────────────
def humans_section_html(humans: dict, iss_telem: dict) -> str:
    if not humans:
        return ""

    cards = []
    # ISS card (with telemetry)
    iss_crew = humans.get("ISS", [])
    if iss_crew:
        telem_html = ""
        if iss_telem:
            alt  = iss_telem.get("altitude", 0)
            vel  = iss_telem.get("velocity", 0)
            lat  = iss_telem.get("latitude", 0)
            lon  = iss_telem.get("longitude", 0)
            vis  = iss_telem.get("visibility", "")
            vis_cls   = {"daylight": "vis-day", "eclipsed": "vis-eclipse"}.get(vis, "vis-night")
            vis_icon  = {"daylight": "☀ Daylight", "eclipsed": "🌑 Eclipse"}.get(vis, "🌙 Night")
            telem_html = f"""
  <div class="telem-row">
    <div class="telem-item">
      <div class="telem-lbl">Altitude</div>
      <div class="telem-val">{alt:,.0f} km</div>
    </div>
    <div class="telem-item">
      <div class="telem-lbl">Velocity</div>
      <div class="telem-val">{vel:,.0f} km/h</div>
    </div>
    <div class="telem-item">
      <div class="telem-lbl">Latitude</div>
      <div class="telem-val">{lat:.2f}°</div>
    </div>
    <div class="telem-item">
      <div class="telem-lbl">Longitude</div>
      <div class="telem-val">{lon:.2f}°</div>
    </div>
    <div class="telem-item">
      <div class="telem-lbl">Visibility</div>
      <div class="telem-val {vis_cls}">{vis_icon}</div>
    </div>
  </div>"""

        crew_items = "".join(
            f'<div class="crew-member"><span class="crew-dot"></span>{n}</div>'
            for n in iss_crew
        )
        cards.append(f"""
<div class="craft-card">
  <div class="craft-header">
    <span class="craft-name">🛸 International Space Station</span>
    <span class="craft-count">{len(iss_crew)} crew</span>
  </div>
  {telem_html}
  <div class="crew-grid">{crew_items}</div>
</div>""")

    # Other craft cards (Tiangong, etc.)
    for craft, crew in sorted(humans.items()):
        if craft == "ISS":
            continue
        crew_items = "".join(
            f'<div class="crew-member"><span class="crew-dot"></span>{n}</div>'
            for n in crew
        )
        icon = "🛸" if "tiangong" in craft.lower() else "🚀"
        cards.append(f"""
<div class="craft-card">
  <div class="craft-header">
    <span class="craft-name">{icon} {craft}</span>
    <span class="craft-count">{len(crew)} crew</span>
  </div>
  <div class="crew-grid">{crew_items}</div>
</div>""")

    total = sum(len(v) for v in humans.values())
    cards_html = "".join(cards)
    return f"""
<div class="humans-section">
  <div class="section-label">👨‍🚀 {total} humans currently in space</div>
  <div class="craft-grid">{cards_html}</div>
</div>"""


# ── Render ─────────────────────────────────────────────────────────────────────
data, all_dishes, dsn_ts = fetch_dsn_data()
humans, iss_telem        = get_humans()
now_str = time.strftime("%Y-%m-%d  %H:%M:%S  UTC")

# Header
st.markdown(f"""
<div class="dsn-header">
  <div>
    <div class="dsn-title">🛰&nbsp; NASA Deep Space Network</div>
    <div class="dsn-subtitle">REAL-TIME COMMUNICATIONS MONITOR</div>
  </div>
  <div class="dsn-right">
    <div class="live-indicator"><span class="live-dot"></span>LIVE</div>
    <div class="dsn-ts">{now_str}</div>
    <div class="dsn-ts" style="color:#2a4a62;font-size:0.68rem;margin-top:2px;">
        DSN TIMESTAMP: {dsn_ts}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# Humans in space
h_html = humans_section_html(humans, iss_telem)
if h_html:
    st.markdown(h_html, unsafe_allow_html=True)

# DSN contacts or idle view
if data:
    stations: dict = defaultdict(lambda: defaultdict(list))
    for r in data:
        stations[r["loc"]][r["dish"]].append(r)

    n_stations = len(stations)
    n_dishes   = sum(len(d) for d in stations.values())
    n_sc       = len(data)

    st.markdown(f"""
<div class="metrics-row">
  <div class="metric-card">
    <div class="metric-value">{n_stations}</div>
    <div class="metric-label">Stations Online</div>
  </div>
  <div class="metric-card">
    <div class="metric-value">{n_dishes}</div>
    <div class="metric-label">Active Dishes</div>
  </div>
  <div class="metric-card">
    <div class="metric-value">{n_sc}</div>
    <div class="metric-label">Spacecraft Links</div>
  </div>
  <div class="metric-card">
    <div class="metric-value">{sum(len(v) for v in humans.values()) if humans else "—"}</div>
    <div class="metric-label">Humans in Space</div>
  </div>
</div>
""", unsafe_allow_html=True)

    html_parts = ['<div class="stations-wrapper">']
    for station_name, dishes in sorted(stations.items()):
        dish_count = len(dishes)
        cards_html = "".join(
            dish_card_html(dish_name, targets, humans)
            for dish_name, targets in sorted(dishes.items())
        )
        html_parts.append(f"""
<div class="station-block">
  <div class="station-header">
    <span class="station-name">{station_name}</span>
    <span class="station-count">{dish_count} dish{'es' if dish_count != 1 else ''} active</span>
  </div>
  <div class="dish-grid">{cards_html}</div>
</div>""")
    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)

elif data is None:
    st.markdown(f'<div class="msg-error">⚠ Fetch error: {dsn_ts}</div>',
                unsafe_allow_html=True)
else:
    parts = ['<div class="stations-wrapper">']
    parts.append('<div class="msg-waiting">📡 No active spacecraft contacts — network status below</div>')
    for station_name, dishes in sorted(all_dishes.items()):
        cards = "".join(
            f'<div class="idle-card">'
            f'<span class="idle-dish">{d["dish"]}</span>'
            f'<span class="idle-activity">{d["activity"] or "Idle"}</span>'
            f'</div>'
            for d in dishes
        )
        parts.append(f"""
<div class="station-block">
  <div class="station-header">
    <span class="station-name">{station_name}</span>
    <span class="station-count">{len(dishes)} dishes</span>
  </div>
  <div class="idle-grid">{cards}</div>
</div>""")
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)

# Footer
st.markdown("""
<div class="dsn-footer">
  <div class="footer-legend">
    <span><span class="band band-S">S</span> 2–4 GHz</span>
    <span><span class="band band-X">X</span> 7.25–8.4 GHz</span>
    <span><span class="band band-K">K</span> 26.5–40 GHz</span>
  </div>
  <div class="footer-legend">
    <span style="color:#00ff88">■</span> Strong (&gt;−120 dBm) &nbsp;
    <span style="color:#ffcc00">■</span> OK (−120 to −140) &nbsp;
    <span style="color:#ff5555">■</span> Weak (&lt;−140 dBm)
  </div>
  <div>DSN · open-notify.org · wheretheiss.at</div>
</div>
""", unsafe_allow_html=True)

# ── Auto-refresh ───────────────────────────────────────────────────────────────
time.sleep(REFRESH_INTERVAL)
st.rerun()
