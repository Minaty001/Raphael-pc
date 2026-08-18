# 🏛️ Raphael v3 — Architecture Specification

Raphael v3 is an event-driven, multi-threaded **Always-Alive AI Desktop Assistant**. The system is
designed to run persistently in the background as a Linux systemd user service (or cross-platform
background service), maintaining environmental awareness, listening for wake words, handling
proactive background tasks, and serving a decoupled React HUD frontend.

---

## 📑 Table of Contents

- [High-Level System Architecture](#-high-level-system-architecture)
- [Core Subsystems](#-core-subsystems)
- [Gateway API & Protocols](#-gateway-api--protocols)
- [Security & Privacy Architecture](#-security--privacy-architecture)
- [Status & Honest Gaps](#-status--honest-gaps)

---

## 📐 High-Level System Architecture

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

---

## 🧩 Core Subsystems

### 1. Persistent Runtime (`raphael/runtime/`)
- **`AlwaysAliveController` (`always_alive.py`)**: Manages the persistent runtime process. UI closes
  do not stop the background loop. Supports 5 modes: `NORMAL`, `FOCUS`, `PAUSE`, `SLEEP`, `EXIT`.
- **`TaskManager` (`tasks.py`)**: Priority-based task queue (`CRITICAL`, `HIGH`, `NORMAL`,
  `BACKGROUND`) backed by SQLite persistence (`.raphael_data/tasks.db`). Features bounded worker
  pools, checkpointing, exponential backoff retry, and **non-blocking dependency scheduling**
  (waiting tasks re-enqueue and wake on dependency completion).
- **`HealthMonitor` (`health_monitor.py`)**: Tracks component health with **truthful status**
  (`listening` vs `connected`) and automatically restarts failed worker threads.

### 2. Voice Subsystem (`raphael/voice/`)
- **Rolling Audio Buffer (`wakeword.py`)**: Continuously monitors the audio stream in a rolling
  buffer without recording full speech until the wake-word trigger. `get_post_wake_audio()` returns
  only audio captured **after** the wake timestamp.
- **Sample-Rate Normalization (`microphone.py`)**: A stateful `Resampler` converts any hardware rate
  (e.g. 44.1 kHz) down to 16 kHz mono PCM before KWS / VAD / STT, so all consumers agree on rate.
- **9-State Audio Machine (`audio_state.py`)**:
  - `OFF` → `LISTENING_WAKE` → `WAKE_DETECTED` → `RECORDING_COMMAND` → `PROCESSING` → `SPEAKING` →
    `PAUSED` / `MUTED` / `ERROR`
- **Speech Pipeline (`stt.py`, `tts.py`, `pipeline.py`)**: Local/cloud STT with Edge-TTS / pyttsx3
  fallback. Supports barge-in interrupt requests.
- **Wake-Word (`wakeword.py`)**:
  - `PorcupineProvider` — process audio in fixed **512-sample frames** (correct Porcupine API).
  - `TranscriptWakeProvider` — low-power transcript-based fallback when Porcupine is unavailable.

### 3. Cognitive Engine & LLM Router (`raphael/brain/`)
- **`CognitiveRuntime` (`cognitive_runtime.py`)**: Coordinates perception, plan generation, tool
  execution, and memory storage.
- **`LLMRouter` (`llm_router.py`)**: Router supporting local (Ollama) and cloud providers (Groq,
  OpenAI, Anthropic) with fallback logic.
- **`Planner` (`planner.py`)**: Decomposes complex goals into multi-step execution graphs.
- **`AttentionManager` & `MetaCognition` (`attention_manager.py`, `meta_cognition.py`)**: Manages
  context budget, context decay, and post-action quality reflection.
- **`ActionVerifier` (`action_verifier.py`)**: Verifies tool execution safety before invoking tools.

### 4. Memory Architecture (`raphael/memory/`)
- **`MemoryManager` (`memory_manager.py`)**: Central memory coordinator managing:
  - **Working Memory**: Active conversation context & transient state.
  - **Episodic Memory**: Recorded events and interaction history.
  - **Semantic Memory**: Knowledge facts and entity relations.
  - **Procedural Memory**: Tool patterns and routine procedures.
  - **Long-Term Memory**: Persistent SQLite database store.
  - **User Model**: User preferences, profile, and habits.
  - **Vector Store**: Semantic similarity search.

### 5. Proactive Background Engine (`raphael/proactive/`)
- **`ProactiveEngine` (`proactive_engine.py`)**: Background loop triggering proactive suggestions
  based on user context.
- **`CuriosityEngine` (`curiosity_engine.py`)**: Idle-time exploration of user tasks and topics.
- **`RoutineEngine` (`routine_engine.py`)**: Scheduled recurring routines.
- **`ContextualReminders` (`contextual_reminders.py`)**: Triggered by time, system state, or user
  activity.
- **`MorningContinuity` (`morning_continuity.py`)**: Morning briefings and unfinished task summaries.

### 6. Security & Policy Enforcement (`raphael/security/`)
- **Risk Hierarchy (`permissions.py`)**:
  - `READ_ONLY`: File inspection, system state queries (auto-approved).
  - `LOW_RISK`: Launch URL, open app, screenshot (auto-approved).
  - `MODERATE`: File writes, app closure, clipboard modifications (logged).
  - `HIGH_RISK`: Arbitrary shell command execution (`run_command`) — requires user confirmation.
- **Confirmation Flow (`confirmation.py`)**: Emits `security.confirmation_required` WS events for
  high-risk actions to request user approval in the HUD.
- **Gateway Auth (`network/auth.py`)**: `verify_token()` checks the shared `websocket.api_token`.
  Tokens are **never logged** — only `token_present` metadata is recorded on failure.

### 7. Extensible Tool Subsystem (`raphael/tools/`)
- **`ToolRegistry` (`registry.py`)**: Central registry for **15** system tools:
  - System: `system_info`, `set_volume`, `get_volume`
  - Media: `take_screenshot`
  - Clipboard: `clipboard_read`, `clipboard_write`
  - Applications: `open_application`, `close_application`
  - Filesystem: `find_file`, `read_file`, `write_file`, `create_folder`
  - Web/Browser: `launch_url`, `search_web`
  - Developer: `run_command` (HIGH_RISK)

### 8. Frontend Assistant Character (`frontend/src/components/character/`)
- **`CharacterStage`**: 2.5D parallax scene (depth layers + perspective floor + contact shadow);
  pointer drives eye-tracking and depth-of-field.
- **`Character`**: Procedural layered SVG anime schoolgirl with real-time expressions, gestures,
  mouth flap, and breathing/weight-shift motion.
- **`anim/engine.ts`**: Single rAF loop writing transforms directly to refs (no React re-render) for
  60fps motion.
- **`CharacterContext.tsx` + `intent.ts`**: Trigger bus mapping runtime state/events → character
  reactions (error, success, hover, click, security confirm).

---

## 📡 Gateway API & Protocols

### WebSocket Protocol (`ws://localhost:8765/ws`)
> **Auth**: connect with `?token=<api_token>`. Loopback admitted only when auth is disabled in
> config; unauthenticated non-loopback clients are rejected (HTTP 1008).

| Channel / Event | Direction | Description |
|---|---|---|
| `runtime.heartbeat` | Server → Client | Periodic heartbeat with uptime, active workers, tasks, voice status |
| `runtime.health` | Server → Client | Full health snapshot of all core components |
| `runtime.mode` | Server → Client / Client → Server | Broadcasts or updates operating mode (`NORMAL`, `FOCUS`, etc.) |
| `audio.state` | Server → Client | Real-time audio machine state transitions |
| `task.created` | Server → Client | New background task added to queue |
| `task.started` | Server → Client | Task execution started |
| `task.progress` | Server → Client | Task progress percentage and step updates |
| `task.completed` | Server → Client | Task finished successfully |
| `task.failed` | Server → Client | Task error with backoff / retry state |
| `security.confirmation_required` | Server → Client | Prompt for high-risk tool approval |

### REST API Endpoints (`http://localhost:8765`)
| Method | Path | Description |
|---|---|---|
| `GET` | `/api/runtime/health` | Detailed health status of all subsystems |
| `POST` | `/api/runtime/mode` | Set runtime mode (`NORMAL`, `FOCUS`, `PAUSE`, `SLEEP`, `EXIT`) |
| `POST` | `/api/runtime/interrupt` | Issue barge-in interrupt to stop current audio/task |
| `GET` | `/api/tasks` | List active, queued, and historical background tasks |
| `POST` | `/api/tasks` | Create a background task (optionally `tool`-backed or a reminder) |
| `POST` | `/api/tasks/{task_id}/pause` | Pause running or queued task |
| `POST` | `/api/tasks/{task_id}/resume` | Resume paused task |
| `POST` | `/api/tasks/{task_id}/cancel` | Cancel task execution |
| `POST` | `/api/tasks/{task_id}/retry` | Manually retry failed task |
| `GET` | `/api/tools` | List registered tools and risk levels |
| `GET` | `/api/memory` | Query working and long-term memory |

---

## 🔒 Security & Privacy Architecture

1. **Decoupled Audio Capture**: Wake-word listening operates on a local rolling PCM buffer. Audio
   recordings are destroyed after command parsing.
2. **Permission Boundary**: High-risk tool calls cannot bypass confirmation. The runtime prompts the
   WebSocket client and awaits approval before proceeding.
3. **Gateway Authentication**: The `/ws` handshake and REST control endpoints call
   `verify_token()`. Auth failures log only `token_present` metadata — never the token itself.
4. **Resource Throttling**: The `ResourceManager` limits CPU/RAM usage. Under high load, non-critical
   background workers are automatically throttled to preserve system stability.

---

## 📊 Status & Honest Gaps

Raphael v3 is a **working foundation**, not yet the fully autonomous cognitive assistant described in
the vision. The architecture (event bus, runtime modes, task engine, memory layers, security gates)
is real and tested. The following are tracked honestly so the UI never over-claims:

**Recently hardened (P0 audit fixes):**
- Microphone capture runs on the captured asyncio loop via `call_soon_threadsafe` (no thread crash).
- Audio resampled to 16 kHz before KWS/VAD/STT.
- Porcupine processes fixed 512-sample frames.
- `get_post_wake_audio()` returns only post-wake audio.
- WebSocket + REST enforce `verify_token()`; auth failures never log tokens.
- Task scheduler no longer blocks on dependency waits.
- API-created tasks execute real work (tool-backed / reminder), not a fake `sleep`.
- Health monitor reports truthful `listening` vs `connected`.

**Maturing (P1/P2 roadmap):**
- Streaming LLM + STT pipelines (currently buffered).
- True embedding-based vector memory (the vector store currently uses bag-of-words similarity).
- Richer autonomous planning/execution (plans exist as data structures; execution loop is partial).
- Real browser automation (current browser tools open URLs / run searches).
- Multimodal screen OCR / vision understanding.
- Per-task CPU/RAM enforcement and universally resumable checkpoints.
