# 🧠 Raphael v3 — Always-Alive AI Desktop Assistant

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141+-green.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18-blue.svg)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5-purple.svg)](https://vitejs.dev/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Raphael** is a persistent, event-driven **Always-Alive AI Desktop Assistant** runtime that
**stays alive in the background** after you close the UI. It maintains environmental awareness,
listens for its wake word, captures following speech, runs multiple background tasks concurrently,
and performs permitted background work **without blocking** your desktop interaction.

> **Design Principle:** Raphael is always *present*, but unobtrusive when idle; immediately
> responsive when called; and capable of useful autonomous background work without taking control
> away from the user.

---

## 📑 Table of Contents

- [What's in v3](#-whats-in-v3-always-alive--cognitive-intelligence)
- [Architecture](#-architecture)
- [Project Status](#-project-status)
- [Prerequisites](#-prerequisites)
- [Quick Start](#-quick-start-localhost)
- [Diagnostics & Testing](#-diagnostics--testing)
- [WebSocket & REST API](#-websocket--rest-api-reference)
- [Runtime Modes](#-runtime-modes)
- [Background Service Setup](#-background-service-setup)
- [Project Layout](#-project-layout)
- [Privacy & Security Model](#-privacy--security-model)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ What's in v3 (Always-Alive + Cognitive Intelligence)

| Capability | Module / Component | Description |
|---|---|---|
| **Always-Alive Runtime** | `raphael/runtime/always_alive.py` | UI close ≠ runtime stop. Runtime keeps running in background. |
| **5 Runtime Modes** | `AlwaysAliveController` | Switch between `NORMAL`, `FOCUS`, `PAUSE`, `SLEEP`, and `EXIT`. |
| **Wake-Word Capture** | `raphael/voice/wakeword.py` | Rolling PCM buffer detects wake-word before capturing command speech. |
| **9-State Audio Machine** | `raphael/voice/audio_state.py` | Tracks voice lifecycle (`OFF`, `LISTENING_WAKE`, `RECORDING`, `SPEAKING`, etc.). |
| **Cognitive Loop & Planner** | `raphael/brain/` | Multi-step reasoning planner, LLM router (Groq/Ollama/OpenAI/Anthropic), attention & metacognition. |
| **Multi-Layered Memory** | `raphael/memory/` | Working memory, episodic events, semantic knowledge, procedural routines, and vector store. |
| **Background Task Engine** | `raphael/runtime/tasks.py` | Priority task queue (`CRITICAL`, `HIGH`, `NORMAL`, `BACKGROUND`) with SQLite persistence & retries. |
| **Proactive Intelligence** | `raphael/proactive/` | Background curiosity exploration, scheduled routines, contextual reminders, morning continuity. |
| **Multimodal Perception** | `raphael/perception/` | Vision screen understanding and unified perception processing. |
| **Resource-Aware Throttling** | `ResourceManager` + `TaskManager` | Monitors CPU/RAM pressure and automatically throttles non-critical workers. |
| **Health Monitor Watchdog** | `raphael/runtime/health_monitor.py` | Tracks component health with truthful status and auto-restarts crashed workers. |
| **Security & Confirmation** | `raphael/security/` | Permission policy model (`READ_ONLY`, `LOW`, `MODERATE`, `HIGH_RISK`) with interactive HUD confirmation gates. |
| **Tool Registry (15 Tools)** | `raphael/tools/` | Native tools for system specs, file operations, web search, app management, screenshot, volume, and shell commands. |
| **WebSocket / REST Gateway** | `raphael/network/api.py` | Real-time event streaming (`runtime.heartbeat`, `task.*`, `audio.*`) and control API — **auth-gated**. |
| **2.5D Anime Assistant UI** | `frontend/src/components/character/` | Procedural layered SVG anime character with real-time expressions, gestures, and 2.5D parallax that reacts to runtime state & events. |
| **Neon React HUD UI** | `frontend/` | Futuristic HUD interface with status pills, task drawer, cognitive brain panel, and feature views. |
| **Background Service Integration** | `scripts/` | Systemd `--user` unit, autostart configuration, and cross-platform system tray. |

---

## 🧱 Architecture

```
                                   ┌────────────────────────────────────────────────────────┐
                                   │                   RAPHAEL REACT HUD                    │
                                   │  Alive Indicator | Task Drawer | Voice Status | Orb    │
                                   │  + 2.5D Anime Assistant (character/)                    │
                                   └───────────────────────────┬────────────────────────────┘
                                                               │  WebSocket ws://localhost:8765/ws  (auth token required)
                                                               │  REST http://localhost:8765/api
                                                               ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                            RAPHAEL ALWAYS-ALIVE RUNTIME                                                │
│                                                                                                                        │
│  ┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐   ┌──────────────────────────────┐  │
│  │   VOICE SUBSYSTEM     │   │   COGNITIVE ENGINE    │   │  BACKGROUND RUNTIME   │   │     PROACTIVE ENGINE         │  │
│  │  • Wake-Word (Buffer) │   │  • Planner / LLM      │   │  • Task Scheduler     │   │  • Curiosity & Routines      │  │
│  │  • 9-State Machine    │   │  • Attention Manager  │   │  • Bounded Worker Pool│   │  • Contextual Reminders      │  │
│  │  • STT / TTS Pipeline │   │  • Metacognition      │   │  • SQLite DB Store    │   │  • Morning Briefing          │  │
│  └───────────┬───────────┘   └───────────┬───────────┘   └───────────┬───────────┘   └──────────────┬───────────────┘  │
│              │                           │                           │                              │                  │
│              └───────────────────────────┼───────────────────────────┴──────────────────────────────┘                  │
│                                          ▼                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                          CORE EVENT BUS & STATE MANAGER                                          │  │
│  └───────┬───────────────────────────────┬───────────────────────────────┬───────────────────────────────┬──────────┘  │
│          │                               │                               │                               │             │
│          ▼                               ▼                               ▼                               ▼             │
│  ┌───────────────┐               ┌───────────────┐               ┌───────────────┐               ┌───────────────┐     │
│  │ MEMORY SYSTEM │               │  PERCEPTION   │               │ SECURITY &    │               │ TOOL REGISTRY │     │
│  │ • Working     │               │ • Screen      │               │ CONFIRMATION  │               │ • 15 System   │     │
│  │ • Episodic    │               │   Understanding│               │ • Risk Levels │               │   Tools       │     │
│  │ • Semantic    │               │ • Multimodal  │               │ • Audit Logs  │               │ • Execution   │     │
│  │ • Vector Store│               │   Integration │               │ • Policy Gate │               │   Sandbox     │     │
│  └───────────────┘               └───────────────┘               └───────────────┘               └───────────────┘     │
│                                                                                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                  RESOURCE MANAGER & HEALTH MONITOR WATCHDOG                                      │  │
│  └──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

The UI is a **decoupled client**. Closing or minimizing it does **not** terminate the runtime
process. Only an explicit **Exit Raphael** command or process shutdown terminates the service.

For an in-depth technical specification, read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
For the **restructured build/study order** (dependency-first KO, not a flat module list), read
[docs/ROADMAP.md](docs/ROADMAP.md).
For the frontend, see [frontend/README.md](frontend/README.md).

---

## 📊 Project Status

Raphael v3 is a **working foundation** with a solid runtime, a decoupled HUD, and a growing
cognitive layer. The backend skeleton (event bus, runtime modes, task engine, memory layers,
security gates) is in place and tested. Some subsystems are still maturing — this is tracked
honestly below so the UI never over-claims what the brain can do.

**Recently fixed (P0 audit hardening):**
- ✅ Microphone capture thread no longer crashes the asyncio loop (`call_soon_threadsafe`).
- ✅ Sample-rate normalization — audio is resampled to 16 kHz before KWS/VAD/STT.
- ✅ Porcupine wake-word now processes fixed 512-sample frames (was per-sample, broken).
- ✅ `get_post_wake_audio()` returns only post-wake audio (not pre-roll).
- ✅ WebSocket + REST now enforce `verify_token()` — no longer open to unauthenticated clients.
- ✅ Auth failures no longer log raw tokens.
- ✅ Task scheduler no longer blocks on dependency waits; dependent tasks re-enqueue and wake on completion.
- ✅ API-created tasks execute real work (tool-backed / reminder) instead of a fake `sleep`.
- ✅ Health monitor reports truthful `"listening"` vs `"connected"` for the WebSocket.

**Known gaps being addressed (P1/P2):**
- Streaming LLM + STT pipelines (currently buffered), true embedding-based vector memory,
  richer autonomous planning/execution, real browser automation, and multimodal screen OCR.

See the in-repo audit notes for the full prioritized roadmap.

---

## 📋 Prerequisites

- **Python** ≥ 3.10 (tested on 3.12)
- **Node.js** ≥ 18 + npm (for the frontend React HUD)
- **Git**
- A running LLM endpoint (Ollama recommended; Groq/OpenAI/Anthropic also supported via the LLM router)
- Optional: microphone + speakers for voice interaction; `pystray` + `Pillow` for the system tray icon

---

## 🚀 Quick Start (Localhost)

Running Raphael in development mode requires **two terminals**:

### 1. Backend — Always-Alive Runtime

```bash
# Clone the repository
git clone https://github.com/Minaty001/Raphael-pc.git
cd Raphael-pc

# Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate            # On Windows: venv\Scripts\activate

# Install backend dependencies
pip install -r requirements.txt

# Start the runtime server
python -m raphael.cli server
```

The runtime initializes the Always-Alive controller, task scheduler, health watchdog, and API
gateway on:
- **WebSocket**: `ws://localhost:8765/ws`  *(requires `?token=<api_token>`)*
- **REST API**: `http://localhost:8765`

> ✅ After this point Raphael is *alive*. You can open, close, or refresh the frontend as much
> as you like — the background runtime keeps operating.

### 2. Frontend — React HUD UI

```bash
# In a separate terminal
cd frontend
npm install
npm run dev
```

Open the printed local URL (default: **http://localhost:5173**). The top bar displays a
**● ALIVE** indicator and a **⚙ N Tasks** drawer trigger, with the 2.5D assistant character on
the Home view reacting to runtime state and events.

### 3. (Optional) Production UI Build

```bash
cd frontend
npm install
npm run build      # Compiles production assets to frontend/dist
npm run preview    # Serves the built UI locally
```

See [frontend/README.md](frontend/README.md) for full frontend documentation.

---

## 🧪 Diagnostics & Testing

Run diagnostics and test suites using the CLI:

```bash
# Environment & subsystem health diagnostic check
python -m raphael.cli doctor

# Run full test suite
python -m raphael.cli test
```

You can also run pytest directly:

```bash
python3 -m pytest tests/
```

And the frontend type-check / build:

```bash
cd frontend
npm run check      # runs `typecheck` then `build`
```

---

## 🔌 WebSocket & REST API Reference

### Real-Time WebSocket Events (`ws://localhost:8765/ws`)

> **Authentication:** connect with `?token=<api_token>` (configured under
> `websocket.api_token`). Loopback connections are admitted when auth is disabled in config.
> The handshake rejects unauthenticated non-loopback clients with HTTP 1008.

| Event Name | Direction | Payload Description |
|---|---|---|
| `runtime.heartbeat` | Server → Client | `{ uptime, active_workers, task_count, voice_state, component_health }` |
| `runtime.health` | Server → Client | Full health snapshot of all core components |
| `runtime.mode` | Bi-directional | `{ mode }` (`NORMAL`, `FOCUS`, `PAUSE`, `SLEEP`, `EXIT`) |
| `audio.state` | Server → Client | `{ state }` (Current 9-state machine value) |
| `task.created` | Server → Client | Task ID, description, priority, and initial state |
| `task.started` / `progress` | Server → Client | Active task progress percentage and status update |
| `task.completed` / `failed` | Server → Client | Execution result, output payload, or error traceback |
| `security.confirmation_required` | Server → Client | Prompt for high-risk action confirmation |

### REST API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/runtime/health` | Returns subsystem component health status |
| `POST` | `/api/runtime/mode` | Sets runtime mode (`NORMAL`, `FOCUS`, `PAUSE`, `SLEEP`, `EXIT`) |
| `POST` | `/api/runtime/interrupt` | Triggers immediate barge-in interrupt for voice/tasks |
| `GET` | `/api/tasks` | Fetches active, queued, and completed background tasks |
| `POST` | `/api/tasks` | Creates a background task (optionally `tool`-backed or a reminder) |
| `POST` | `/api/tasks/{id}/pause` | Pauses a specific background task |
| `POST` | `/api/tasks/{id}/resume` | Resumes a paused background task |
| `POST` | `/api/tasks/{id}/cancel` | Cancels background task execution |
| `POST` | `/api/tasks/{id}/retry` | Retries execution of a failed task |
| `GET` | `/api/tools` | Lists all 15 registered tools and permission levels |

---

## ⚙️ Runtime Modes

| Mode | Behavior |
|---|---|
| **NORMAL** | Full environmental awareness, wake-word detection active, background tasks execute normally. |
| **FOCUS** | Background tasks throttled, non-critical notifications suppressed, wake-word remains enabled. |
| **PAUSE** | Voice capture paused, **background tasks continue** operating (privacy mode without stopping work). |
| **SLEEP** | Wake-word, voice capture, and cognitive background loops paused; critical reminders stay active. |
| **EXIT** | Checkpoints memory, saves task queues, safely stops worker threads, and shuts down the runtime process. |

---

## 🖥️ Background Service Setup

### Linux (systemd --user unit — No root required)

To run Raphael as a persistent user service starting automatically on login:

```bash
chmod +x scripts/install_runtime.sh
./scripts/install_runtime.sh
```

This script installs `raphael-runtime.service` into `~/.config/systemd/user/` and creates a
desktop autostart entry.

Monitor service logs:
```bash
journalctl --user -u raphael-runtime -f
```

### System Tray Icon

```bash
# Run system tray icon (cross-platform)
python scripts/raphael_tray.py
```

### Windows Setup

Run `python -m raphael.cli server` at user logon via Task Scheduler ("Run with highest
privileges" off). The tray icon runs cross-platform via `pystray`.

---

## 🗂️ Project Layout

```
Raphael-pc/
├── raphael/                    # Python Backend (Always-Alive Runtime)
│   ├── brain/                  # Cognitive engine (planner, LLM router, attention, metacognition)
│   ├── core/                   # Core runtime loop, configuration, event bus, resource manager
│   ├── learning/               # Learning engine, reflection engine, skill acquisition
│   ├── memory/                 # Multi-layer memory (working, episodic, semantic, procedural, long-term)
│   ├── network/                # FastAPI REST API & WebSocket gateway server (auth-gated)
│   ├── perception/             # Unified perception & screen vision understanding
│   ├── proactive/              # Proactive engine (curiosity, routines, reminders, morning continuity)
│   ├── runtime/                # Always-alive controller, task queue & DB, health monitor watchdog
│   ├── security/               # Security policies, risk permissions, confirmation flow, audit log
│   ├── tools/                  # 15 Built-in tools (system, filesystem, app, browser, dev, media)
│   ├── voice/                  # Voice pipeline (audio state machine, wake-word rolling buffer, STT, TTS)
│   ├── cli.py                  # CLI entry point (server, test, doctor)
│   └── runtime_launcher.py     # Background service launcher script
├── frontend/                   # React + Vite HUD Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── character/      # 2.5D anime assistant (engine, Character, CharacterStage, intent, context)
│   │   │   ├── layout/          # HUD panels, status indicators, confirmation modal, drawers
│   │   │   ├── brain/           # RaphaelOrb cognitive visual
│   │   │   └── ...              # Other interactive panels
│   │   ├── pages/              # HUD views (Home, Memory, System, Tools, Goals, Settings, etc.)
│   │   ├── stores/             # Global state management (raphaelStore)
│   │   └── websocket.ts         # Real-time WebSocket manager
│   ├── package.json            # includes `dev`, `build`, `preview`, `typecheck`, `check`
│   └── typecheck.mjs           # Standalone TypeScript type-check (tsconfig.json driven)
├── docs/                       # Comprehensive documentation
│   └── ARCHITECTURE.md         # Detailed technical architecture specification
├── scripts/                    # Desktop integration scripts (systemd unit, autostart, tray icon)
├── tests/                      # Python pytest suite
├── requirements.txt            # Backend Python dependencies
└── README.md                   # Main project documentation
```

---

## 🔒 Privacy & Security Model

- **Auth-gated gateway**: The WebSocket handshake and REST control endpoints verify a token
  (`network.auth.verify_token`). Loopback is admitted only when auth is disabled in config.
  Auth failures log metadata only — never the token itself.
- **Separation of Wake-Word and Speech Logging**: Wake-word monitoring uses a localized rolling
  audio buffer. Full speech is only captured after wake-word verification and is discarded
  post-processing.
- **Risk-Gated Execution**: Tools are categorized by risk level (`READ_ONLY`, `LOW`,
  `MODERATE`, `HIGH_RISK`). High-risk tools like `run_command` require explicit user confirmation
  via the HUD UI.
- **Worker Isolation**: Background worker tasks execute in bounded thread pools to prevent
  blocking voice capture or real-time responsiveness.

---

## 🤝 Contributing

1. Fork the repository and create a feature branch (`git checkout -b feature/amazing-feature`)
2. Ensure tests pass (`python -m raphael.cli test`)
3. Ensure frontend builds clean and type-checks (`cd frontend && npm run check`)
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch and open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the repository for details.
