# 🧠 Raphael v3 — Always-Alive AI Desktop Assistant

Raphael is a persistent, event-driven AI assistant runtime that **stays alive in
the background** after you close the UI. It quietly maintains awareness, listens
for its wake word, captures your following speech immediately, runs multiple
background tasks concurrently, and does permitted background work **without
blocking** your interaction.

> **Design principle:** Raphael is always *present*, but almost invisible when not
> needed; immediately responsive when called; and capable of useful background
> work without taking control away from you.

---

## ✨ What's in v3 (Always-Alive + Background Intelligence)

| Capability | Where |
|---|---|
| Always-alive runtime (UI close ≠ runtime stop) | `raphael/runtime/always_alive.py` |
| Runtime modes: NORMAL / FOCUS / PAUSE / SLEEP / EXIT | `AlwaysAliveController` |
| Wake-word → immediate command capture (rolling audio buffer) | `raphael/voice/wakeword.py` |
| 9-state audio machine (wake / command / speaking / paused …) | `raphael/voice/audio_state.py` |
| Background Task Engine: priority queue + bounded worker pool | `raphael/runtime/tasks.py` |
| SQLite task persistence + checkpointing + retry | `raphael/runtime/tasks.py` |
| Resource-aware throttling (RAM/CPU pressure → pause noncritical) | `ResourceManager` + `TaskManager` |
| Health monitor + watchdog (crashed workers auto-restart) | `raphael/runtime/health_monitor.py` |
| Heartbeat + `task.*` WebSocket events → live UI | `raphael/network/api.py` |
| Dedicated `raphael-runtime` process (client/server split) | `raphael/runtime_launcher.py` |
| System tray (ALIVE / LISTENING / …) + systemd --user unit | `scripts/` |
| Neon HUD UI: ALIVE pill, task drawer, runtime panel, voice status | `frontend/src/components/{runtime,tasks,voice}` |

---

## 🧱 Architecture

```
┌──────────────────────────────────────────────┐
│            RAPHAEL ALWAYS-ALIVE RUNTIME      │
│  Wake Word ─▶ Voice Capture ─▶ Cognition      │
│  Background Task Scheduler (priority queue)   │
│  Memory / Screen / Notification Workers       │
│  Resource Manager + Health Monitor + Watchdog  │
│  WebSocket Gateway ──▶ UI (client)            │
└──────────────────────────────────────────────┘

raphael-runtime  (persistent process / service)
      │  WebSocket  ws://localhost:8765/ws
      ▼
raphael-ui       (React client — can be opened/closed freely)
```

The UI is a **client**. Closing or minimizing it does **not** terminate the
runtime. Only **Exit Raphael** shuts the runtime down.

---

## 📋 Prerequisites

- **Python** ≥ 3.10 (tested on 3.12)
- **Node.js** ≥ 18 + npm (for the frontend)
- **Git**
- A running LLM endpoint (Ollama recommended; OpenAI/Anthropic also supported via the LLM router)
- Optional: microphone + speakers for voice; `pystray` for the tray icon

---

## 🚀 Quick start (localhost)

You need **two terminals** (or run the runtime as a service — see below):

### 1. Backend — the Always-Alive Runtime

```bash
# clone (if you haven't)
git clone https://github.com/Minaty001/Raphael-pc.git
cd Raphael-pc

# create an isolated Python env (recommended)
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate

# install backend dependencies
pip install -r requirements.txt

# start the runtime + WebSocket gateway
python -m raphael.cli server
```

The runtime boots, starts the Always-Alive controller, the health monitor, the
background task engine, and serves the WebSocket + REST API on
**`ws://localhost:8765/ws`** and **`http://localhost:8765`**.

> ✅ After this point Raphael is *alive*. You can open/close the UI as much as
> you like — the runtime keeps running.

### 2. Frontend — the HUD UI

```bash
cd frontend
npm install
npm run dev
```

Open the printed URL (default **http://localhost:5173**). The top bar shows a
**● ALIVE** pill and a **⚙ N Tasks** indicator. Click them for the Runtime Panel
and Background Task Drawer.

### 3. (Optional) Production UI build

```bash
cd frontend
npm install
npm run build      # outputs to frontend/dist
npm run preview    # serve the built UI
```

---

## 🧪 Verify it's working

```bash
# from the repo root, with the venv active
python -m raphael.cli doctor     # environment + subsystem diagnostics
python -m raphael.cli test       # run the test suite (incl. tests/test_always_alive.py)
```

The always-alive logic is covered by `tests/test_always_alive.py`:

```
tests/test_always_alive.py  9 passed
  - wake-word detection + command stripping + rolling buffer
  - audio state machine transitions
  - health monitor snapshot
  - task priority ordering, lifecycle, resource throttling, execution
```

---

## 🔌 WebSocket / REST API

**WebSocket** `ws://localhost:8765/ws` emits (among others):

| Event | Payload |
|---|---|
| `runtime.heartbeat` | `{ uptime, workers, tasks, voice, components }` |
| `runtime.health` | full component health snapshot |
| `runtime.mode` | `{ mode }` |
| `audio.state` | `{ state }` (9-state machine) |
| `task.created / started / progress / paused / resumed / waiting / completed / failed / cancelled` | task snapshot |

**REST** (used by the UI to fetch/push state):

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/runtime/health` | component health |
| POST | `/api/runtime/mode` | set `NORMAL/FOCUS/PAUSE/SLEEP/EXIT` |
| POST | `/api/runtime/interrupt` | barge-in / stop TTS |
| GET | `/api/tasks` | list background tasks |
| POST | `/api/tasks/{id}/pause\|resume\|cancel\|retry` | control a task |

---

## ⚙️ Runtime modes

| Mode | Behavior |
|---|---|
| **NORMAL** | Full awareness, wake-word active, background tasks run. |
| **FOCUS** | Background tasks reduced, noncritical notifications suppressed, wake-word stays. |
| **PAUSE** | Voice paused, **background tasks continue** (privacy without stopping work). |
| **SLEEP** | Wake-word + voice + cognitive background disabled; scheduler + critical reminders remain. |
| **EXIT** | Save memory, checkpoint tasks, close workers/audio/WS, shut down. |

Switch modes from the **Runtime Panel** in the UI, or via the tray / REST API.

---

## 🖥️ Run as a background service (always start with your session)

### Linux (systemd --user — no root needed)

```bash
chmod +x scripts/install_runtime.sh
./scripts/install_runtime.sh --user            # installs unit, enables --now
```

This installs `raphael-runtime.service` into `~/.config/systemd/user/`,
enables it, and starts it now. Logs:

```bash
journalctl --user -u raphael-runtime -f
```

### Tray icon (Linux)

```bash
pip install pystray pillow        # if not already present
python scripts/raphael_tray.py     # shows ● ALIVE / ● LISTENING / … menu
```

### Windows

Run `python -m raphael.cli server` at logon (Task Scheduler → "Run with
highest privileges" **off** — no admin required). A `pystray` tray is
cross-platform; enable startup via the Settings → Background Mode toggle in-app.

---

## 🗂️ Project layout

```
Raphael-pc/
├── raphael/                 # Python backend (the runtime)
│   ├── core/                # runtime loop, config, event bus, resource mgr
│   ├── runtime/             # always_alive, tasks, health_monitor, tasks DB
│   ├── voice/               # audio_state, wakeword (rolling buffer), stt, tts
│   ├── network/             # FastAPI api + websocket gateway
│   ├── memory/ brain/ learning/ ...
│   └── runtime_launcher.py # entry point for the persistent service
├── frontend/               # React + Vite + Tailwind HUD
│   └── src/
│       ├── components/runtime/   # AliveIndicator, RuntimePanel
│       ├── components/tasks/     # BackgroundTaskDrawer
│       ├── components/voice/     # VoiceStatus (privacy-aware)
│       └── App.tsx, websocket.ts, types.ts
├── scripts/                # systemd unit, tray, install helper
├── tests/test_always_alive.py
├── requirements.txt
└── README.md
```

---

## 🔒 Privacy & safety

- **Wake listener vs command capture are distinct** (UI shows both): the mic is
  open for *wake detection* only; *full speech* is captured only after the wake
  word. Raphael never secretly records full conversations.
- Background work runs in bounded worker pools and can never block the voice
  path or the UI.
- Security-sensitive tool calls still go through the interactive confirmation
  flow; background tasks cannot bypass it.

---

## 🤝 Contributing

1. Fork & branch (`git checkout -b feature/...`)
2. `python -m raphael.cli test` must stay green
3. `cd frontend && npm run build` must succeed
4. Open a PR

---

## 📄 License

See repository for license details.
