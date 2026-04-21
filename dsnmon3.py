import urllib.request
import xml.etree.ElementTree as ET
import time
import os

# --- Constants & Mapping ---
URL = "https://eyes.nasa.gov/dsn/data/dsn.xml"
AU_KM = 149597870.7
LIGHT_SPEED = 299792.458

# Mission Name Lookup Table
MISSION_NAMES = {
    "JNO": "Juno (Jupiter)",
    "VGR1": "Voyager 1",
    "VGR2": "Voyager 2",
    "MSL": "Curiosity Rover (Mars)",
    "M20": "Perseverance Rover (Mars)",
    "MAVEN": "MAVEN (Mars)",
    "MRO": "Mars Recon. Orbiter",
    "ODY": "Mars Odyssey",
    "TGO": "ExoMars Trace Gas Orbiter",
    "MEX": "Mars Express",
    "EMM": "Hope (Mars/UAE)",
    "ESCB": "EscaPADE (Mars)",
    "KPLO": "Danuri (Moon/Korea)",
    "EM2": "Artemis II",
    "ORBT": "Lunar Recon. Orbiter",
    "CAPL": "CAPSTONE (Moon)",
    "PARK": "Parker Solar Probe",
    "SOLO": "Solar Orbiter",
    "BEPI": "BepiColombo (Mercury)",
    "JUICE": "JUICE (Jupiter)",
    "LUCY": "Lucy (Asteroids)",
    "PSY": "Psyche (Asteroids)",
    "OSIRIS": "OSIRIS-REx",
    "JWST": "James Webb Telescope",
    "EUCL": "Euclid Telescope",
    "NEOWI": "NEOWISE",
    "DSCOV": "DSCOVR",
    "ACE": "Advanced Comp. Explorer",
    "SOHO": "SOHO",
    "WIND": "WIND",
    "VOY1": "Voyager 1", 
    "VOY2": "Voyager 2",
    "ORX": "OSIRIS-REx",
    "CHDR": "Chandra",
    "MMS1": "Magnetospheric Multiscale 1",
    "MMS2": "Magnetospheric Multiscale 2",
    "MMS3": "Magnetospheric Multiscale 3",
    "MMS4": "Magnetospheric Multiscale 4",
    "CAPS": "CAPSTONE",
    "SOHO": "Solar & Heliospheric Observ.",
    "EURC": "Europa Clipper",
}

# UI Colors
CYAN, YELLOW, GREEN, RED, BOLD, RESET = '\033[96m', '\033[93m', '\033[92m', '\033[91m', '\033[1m', '\033[0m'

def fetch_dsn_data():
    try:
        req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            root = ET.fromstring(response.read())
        
        rows = []
        current_station = "Unknown"
        dsn_ts = root.findtext("timestamp") or "Live"

        for child in root:
            if child.tag == "station":
                current_station = child.get("friendlyName", "Unknown")
            
            elif child.tag == "dish":
                dish_name = child.get("name", "??")
                
                # Signal Map: Capturing Downlink
                down_signals = {
                    sig.get("spacecraft", "").upper(): {
                        "p": sig.get("power"),
                        "rate": sig.get("dataRate"),
                        "band": sig.get("band")
                    } 
                    for sig in child.findall("downSignal") if sig.get("spacecraft")
                }

                # Signal Map: Capturing Uplink
                up_signals = {
                    sig.get("spacecraft", "").upper(): {
                        "p": sig.get("power"),
                        "rate": sig.get("dataRate"),
                        "band": sig.get("band")
                    } 
                    for sig in child.findall("upSignal") if sig.get("spacecraft")
                }

                # Targets
                for target in child.findall("target"):
                    code = (target.get("name") or "").upper()
                    if not code or code in ["DSN", "DSS", "NONE", "---"]:
                        continue

                    full_name = MISSION_NAMES.get(code, code)

                    # Distance logic
                    km_val = target.get("uplegRange") or target.get("downlegRange")
                    rtlt_val = target.get("rtlt")
                    dist_str = "---"
                    rtlt_str = "---"

                    try:
                        # Process RTLT
                        if rtlt_val and float(rtlt_val) < 60:
                            rtlt_str = f"{float(rtlt_val)} sec"
                        elif rtlt_val and float(rtlt_val) > 60:
                            rtlt_str = f"{float(rtlt_val) / 60:,.2f} min"
                        
                        # Process Distance
                        if km_val and float(km_val) > 0:
                            km = float(km_val)
                        elif rtlt_val and float(rtlt_val) > 0:
                            km = (float(rtlt_val) / 2) * LIGHT_SPEED
                        if km < 999999:
                            dist_str = f"{km/1e3}K km"
                        elif km >999999:
                            dist_str = f"{km/1e6}M km"
                    except: pass

                    # Process Downlink
                    dsig = down_signals.get(code, {})
                    dp_val = dsig.get("p")
                    dr_val = dsig.get("rate")
                    dband = dsig.get("band") or "---"
                    
                    dp_str, dp_col = "---", RESET
                    drate_str = "---"

                    if dp_val and dp_val != "none":
                        dp_str = f"{dp_val} dBm"
                        try:
                            dbm = float(dp_val)
                            dp_col = GREEN if dbm > -120 else YELLOW if dbm > -140 else RED
                        except: pass
                    
                    if dr_val and dr_val != "none":
                        try:
                            drate_str = f"{float(dr_val)/1e6:,.2f} Mb/s"
                        except: pass

                    # Process Uplink
                    usig = up_signals.get(code, {})
                    up_val = usig.get("p")
                    uband = usig.get("band") or "---"
                    up_str = f"{up_val} kW" if (up_val and up_val != "none") else "---"

                    rows.append({
                        "loc": current_station, "dish": dish_name, "sc": full_name,
                        "dpow": dp_str, "dcol": dp_col, "dist": dist_str, "rtlt": rtlt_str,
                        "drate": drate_str, "upow": up_str, 
                        "dband": dband, "uband": uband
                    })
        return rows, dsn_ts
    except Exception as e:
        return None, str(e)

def main():
    try:
        while True:
            print("\033[H\033[J", end="")
            data, ts = fetch_dsn_data()
            
            # Adjusted width for new column
            width = 155
            print(f"{CYAN}{BOLD}{'=' * width}")
            print(f" NASA DEEP SPACE NETWORK LIVE | {time.strftime('%H:%M:%S')} | DSN Time: {ts}")
            print(f"{'=' * width}{RESET}")
            
            # Updated Header
            header = f"{'STATION':<12} | {'DISH':<5} | {'SPACECRAFT':<30} | {'UP FREQ':<3} | {'UP PWR (kW)':<6} | {'DOWN FREQ':<1} | {'DWN PWR (dBm)':<15} | {'DATA RATE':<10} | {'DISTANCE':<12} | {'LIGHT TRIP'}"
            print(f"{BOLD}{header}{RESET}")
            print("-" * width)

            if data is None:
                print(f"{RED} >> Error: {ts}{RESET}")
            elif not data:
                print(f"{YELLOW} >> Waiting for active spacecraft...{RESET}")
            else:
                for r in sorted(data, key=lambda x: (x['loc'], x['dish'])):
                    down_fmt = f"{r['dcol']}{r['dpow']:<15}{RESET}"
                    # Print row with RTLT
                    print(f"{r['loc']:<12} | {r['dish']:<5} | {YELLOW}{r['sc']:<30}{RESET} | {r['uband']:<7} | {r['upow']:<11} | {r['dband']:<9} | {down_fmt} | {r['drate']:<10} | {r['dist']:<12} | {r['rtlt']}")

            print(f"\n{CYAN}{'=' * width}{RESET}")
            print ("FREQ : S = 2-4GHz,  X = 7.25-8.4 GHz,  K = 26.5-40GHz")
            print(" Update: 5s. Ctrl+C to quit.")
            time.sleep(5)
            
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Terminated.{RESET}\n")

if __name__ == "__main__":
    main()