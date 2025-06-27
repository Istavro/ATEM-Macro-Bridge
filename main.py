import PyATEMMax
import requests
from fastapi import FastAPI
import Config
import uvicorn
import threading
import time

# ───‑‑‑  CONFIG  ‑‑‑─────────────────────────────────────────────────────────────
ATEM_IP        = "127.0.0.1"          # Change if your switcher lives elsewhere
COMPANION_URL  = "http://127.0.0.1:8000"
MACRO_RANGE    = range(0, 19)         # 0‑18 inclusive
POLL_INTERVAL  = 0.05                 # seconds between ATEM polls
# ────────────────────────────────────────────────────────────────────────────────

# ───‑‑‑  Connect to ATEM switcher  ‑‑‑──────────────────────────────────────────
switcher = PyATEMMax.ATEMMax()
switcher.connect(ATEM_IP)
switcher.waitForConnection()
#────────────────────────────────────────────────────────────────────────────────

app = FastAPI()
TimedOutMacro = set()   

@app.delete("/macro-lockout/{page}/{row}/{column}")
def MacroLockout(page:int, row:int, column:int):
    TimedOutMacro.remove(f"{page}/{row}/{column}")
    return

def PollingLoop():
    while True:
        MacroUsed = switcher.macro.runStatus.index
        TranslatedMacro = Config.MacroDictionary[MacroUsed]
        if MacroUsed in MACRO_RANGE and TranslatedMacro not in TimedOutMacro:
            requests.post(f"{COMPANION_URL}/api/location/{TranslatedMacro}/press")
            TimedOutMacro.append(TranslatedMacro)
        time.sleep(POLL_INTERVAL)

# Start the polling loop in a background thread.
threading.Thread(target=PollingLoop, daemon=True).start()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)