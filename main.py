import PyATEMMax
import requests
from fastapi import FastAPI
import Config
import uvicorn
import threading
import time
import logging

# ───‑‑‑  CONFIG  ‑‑‑─────────────────────────────────────────────────────────────
ATEM_IP        = "192.168.8.180"          # Change if your switcher lives elsewhere
COMPANION_URL  = "http://127.0.0.1:8000"
MACRO_RANGE    = range(0, 19)         # 0‑18 inclusive
POLL_INTERVAL  = 0.05                 # seconds between ATEM polls
# ────────────────────────────────────────────────────────────────────────────────

# ───‑‑‑  Setup Logging  ‑‑‑─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
# ────────────────────────────────────────────────────────────────────────────────

# ───‑‑‑  Connect to ATEM switcher  ‑‑‑──────────────────────────────────────────
switcher = PyATEMMax.ATEMMax()
switcher.connect(ATEM_IP)
switcher.waitForConnection()
logging.info(f"Connected to ATEM at {ATEM_IP}")
#────────────────────────────────────────────────────────────────────────────────

app = FastAPI()
TimedOutMacro = set()   

# Receives a signal from companion to unlock the timed out macro at the end of its execution
@app.delete("/macro-lockout/{page}/{row}/{column}")
def MacroLockout(page:int, row:int, column:int):
    TimedOutMacro.discard(f"{page}/{row}/{column}")
    return

# Infinite loop that polls the ATEM switcher for macros and sends POST requests to Companion when a macro is detected and not timed out.
def PollingLoop():
    while True:
        try:
            MacroUsed = switcher.macro.runStatus.index
        except Exception as e:
            logging.error(f"Error reading macro status from ATEM: {e}")
            time.sleep(POLL_INTERVAL)
            continue
        if MacroUsed not in MACRO_RANGE:
            continue
        TranslatedMacro = Config.MacroDictionary.get(MacroUsed)
        if TranslatedMacro and TranslatedMacro not in TimedOutMacro:
            try:
                requests.post(f"{COMPANION_URL}/api/location/{TranslatedMacro}/press")
                TimedOutMacro.add(TranslatedMacro)
                logging.info(f"Received Macro {MacroUsed} and sent POST for macro '{TranslatedMacro}'")
            except Exception as e:
                logging.error(f"Received Macro {MacroUsed} and failed to POST macro '{TranslatedMacro}': {e}")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    threading.Thread(target=PollingLoop, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=9000)