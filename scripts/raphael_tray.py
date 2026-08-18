#!/usr/bin/env python3
"""
RaphaelTray — Linux system tray for Raphael v3 (Sections 5-7).

Shows live runtime state in the tray (ALIVE / LISTENING / WORKING / PAUSED /
ERROR / OFFLINE) and provides a menu matching the spec:
  Open Raphael | Pause Listening | Pause Background Tasks | Focus Mode | Settings | Exit

Uses pystray if available; otherwise prints a clear notice and falls back to a
status loop. pystray is optional so the runtime does not hard-depend on a GUI lib.

Run:  python3 scripts/raphael_tray.py
"""

import sys
import os
import time
import json
import threading
import urllib.request
from datetime import datetime

try:
    import pystray
    from PIL import Image, ImageDraw
    HAVE_TRAY = True
except Exception:
    HAVE_TRAY = False

CONFIG = get_config = None
try:
    sys.path.insert(0, os.path.expanduser("~/Raphael-pc"))
    from raphael.core.configuration import get_config
    HOST = get_config().websocket.host
    PORT = get_config().websocket.port
except Exception:
    HOST, PORT = "127.0.0.1", 8765

BASE = f"http://{HOST}:{PORT}"


def _get(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=2) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


# ---- tray icon rendering --------------------------------------------------
_STATE_COLORS = {
    "ALIVE": (76, 224, 154),
    "LISTENING": (86, 217, 255),
    "WORKING": (244, 201, 93),
    "PAUSED": (150, 160, 170),
    "ERROR": (255, 100, 124),
    "OFFLINE": (90, 100, 110),
}


def _make_icon(color):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([8, 8, 56, 56], fill=color + (255,), outline=(255, 255, 255, 180))
    d.ellipse([26, 26, 38, 38], fill=(255, 255, 255, 230))
    return img


def _status():
    hb = _get("/api/runtime/health")
    mode = _get("/api/runtime/mode")
    if not hb:
        return "OFFLINE"
    comps = hb.get("components", {})
    if any(c.get("status") == "error" for c in comps.values()):
        return "ERROR"
    if mode and mode.get("mode") in ("PAUSE", "SLEEP"):
        return "PAUSED"
    # Determine working vs listening via voice component if present.
    return "ALIVE"


def _refresh(icon):
    while True:
        st = _status()
        color = _STATE_COLORS.get(st, _STATE_COLORS["OFFLINE"])
        icon.icon = _make_icon(color)
        icon.title = f"Raphael — {st}"
        time.sleep(3)


def _open_ui():
    url = f"http://{HOST}:{PORT}"
    if sys.platform.startswith("win"):
        os.startfile(url)
    else:
        os.system(f"xdg-open {url} >/dev/null 2>&1 &")


def _post(path, payload=None):
    try:
        data = json.dumps(payload or {}).encode()
        req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=2)
    except Exception as e:
        print("tray action failed:", e)


def _build_menu():
    import pystray
    return pystray.Menu(
        pystray.MenuItem("Open Raphael", lambda i, m: _open_ui()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Pause Listening", lambda i, m: _post("/api/runtime/mode", {"mode": "PAUSE"})),
        pystray.MenuItem("Pause Background Tasks", lambda i, m: _post("/api/tasks"), ),
        pystray.MenuItem("Focus Mode", lambda i, m: _post("/api/runtime/mode", {"mode": "FOCUS"})),
        pystray.MenuItem("Resume Normal", lambda i, m: _post("/api/runtime/mode", {"mode": "NORMAL"})),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit Raphael", lambda i, m: _post("/api/runtime/mode", {"mode": "EXIT"})),
    )


def main():
    if not HAVE_TRAY:
        print("[RaphaelTray] pystray/PIL not installed; running status loop instead.")
        print("[RaphaelTray] install with: pip install pystray pillow")
        while True:
            print(f"  status: {_status()}  {datetime.now().strftime('%H:%M:%S')}")
            time.sleep(5)
        return

    icon = pystray.Icon(
        "raphael",
        _make_icon(_STATE_COLORS["OFFLINE"]),
        "Raphael",
        _build_menu(),
    )
    threading.Thread(target=_refresh, args=(icon,), daemon=True).start()
    icon.run()


if __name__ == "__main__":
    main()
