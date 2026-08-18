# 🏛️ Raphael v3 — Architecture Specification

Raphael v3 is an event-driven, multi-threaded **Always-Alive AI Desktop Assistant**. The system is designed to run persistently in the background as a Linux systemd user service (or cross-platform background service), maintaining environmental awareness, listening for wake words, handling proactive background tasks, and serving a decoupled React HUD frontend.

---

## 📐 High-Level System Architecture

```
                                   ┌────────────────────────────────────────────────────────┐
                                   │                   RAPHAEL REACT HUD                    │
                                   │  Alive Indicator | Task Drawer | Voice Status | Orb    │
                                   └───────────────────────────┬────────────────────────────┘
                                                               │  WebSocket ws://localhost:8765/ws
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
- **`AlwaysAliveController` (`always_alive.py`)**: Manages the persistent runtime process. UI closes do not stop the background loop. Supports 5 modes: `NORMAL`, `FOCUS`, `PAUSE`, `SLEEP`, `EXIT`.
- **`TaskManager` (`tasks.py`)**: Priority-based task queue (`CRITICAL`, `HIGH`, `NORMAL`, `BACKGROUND`) backed by SQLite persistence (`.raphael_data/tasks.db`). Features bounded worker pools, checkpointing, and exponential backoff retry.
- **`HealthMonitor` (`health_monitor.py`)**: Watchdog process tracking component health and automatically restarting failed worker threads.

### 2. Voice Subsystem (`raphael/voice/`)
- **Rolling Audio Buffer (`wakeword.py`)**: Continuously monitors audio stream in a rolling buffer without recording full speech until wake-word trigger.
- **9-State Audio Machine (`audio_state.py`)**:
  - `OFF` → `LISTENING_WAKE` → `WAKE_DETECTED` → `RECORDING_COMMAND` → `PROCESSING` → `SPEAKING` → `PAUSED` / `MUTED` / `ERROR`
- **Speech Pipeline (`stt.py`, `tts.py`, `pipeline.py`)**: Fast local/cloud STT with Edge-TTS / pyttsx3 fallback. Supports barge-in interrupt requests.

### 3. Cognitive Engine & LLM Router (`raphael/brain/`)
- **`CognitiveRuntime` (`cognitive_runtime.py`)**: Coordinates perception, plan generation, tool execution, and memory storage.
- **`LLMRouter` (`llm_router.py`)**: Router supporting local (Ollama) and cloud providers (Groq, OpenAI, Anthropic) with fallback logic.
- **`Planner` (`planner.py`)**: Decomposes complex goals into multi-step execution graphs.
- **`AttentionManager` & `MetaCognition` (`attention_manager.py`, `meta_cognition.py`)**: Manages context budget, context decay, and post-action quality reflection.
- **`ActionVerifier` (`action_verifier.py`)**: Verifies tool execution safety before invoking tools.

### 4. Memory Architecture (`raphael/memory/`)
- **`MemoryManager` (`memory_manager.py`)**: Central memory coordinator managing:
  - **Working Memory**: Active conversation context & transient state.
  - **Episodic Memory**: Recorded events and interaction history.
  - **Semantic Memory**: Knowledge facts and entity relations.
  - **Procedural Memory**: Tool patterns and routine procedures.
  - **Long-Term Memory**: Persistent SQLite database store.
  - **User Model**: User preferences, profile, and habits.
  - **Vector Store**: Semantic similarity search embeddings.

### 5. Proactive Background Engine (`raphael/proactive/`)
- **`ProactiveEngine` (`proactive_engine.py`)**: Background loop triggering proactive suggestions based on user context.
- **`CuriosityEngine` (`curiosity_engine.py`)**: Idle-time exploration of user tasks and topics.
- **`RoutineEngine` (`routine_engine.py`)**: Scheduled recurring routines.
- **`ContextualReminders` (`contextual_reminders.py`)**: Triggered by time, system state, or user activity.
- **`MorningContinuity` (`morning_continuity.py`)**: Morning briefings and unfinished task summaries.

### 6. Security & Policy Enforcement (`raphael/security/`)
- **Risk Hierarchy (`permissions.py`)**:
  - `READ_ONLY`: File inspection, system state queries (auto-approved).
  - `LOW_RISK`: Launch URL, open app, screenshot (auto-approved).
  - `MODERATE`: File writes, app closure, clipboard modifications (logged).
  - `HIGH_RISK`: Arbitrary shell command execution (`run_command`) — requires user confirmation.
- **Confirmation Flow (`confirmation.py`)**: Emits `security.confirmation_required` WS events for high-risk actions to request user approval in the HUD.

### 7. Extensible Tool Subsystem (`raphael/tools/`)
- **`ToolRegistry` (`registry.py`)**: Central registry for 15 system tools:
  - System: `system_info`, `set_volume`, `get_volume`
  - Media: `take_screenshot`
  - Clipboard: `clipboard_read`, `clipboard_write`
  - Applications: `open_application`, `close_application`
  - Filesystem: `find_file`, `read_file`, `write_file`, `create_folder`
  - Web/Browser: `launch_url`, `search_web`
  - Developer: `run_command` (HIGH_RISK)

---

## 📡 Gateway API & Protocols

### WebSocket Protocol (`ws://localhost:8765/ws`)

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
| `POST` | `/api/tasks/{task_id}/pause` | Pause running or queued task |
| `POST` | `/api/tasks/{task_id}/resume` | Resume paused task |
| `POST` | `/api/tasks/{task_id}/cancel` | Cancel task execution |
| `POST` | `/api/tasks/{task_id}/retry` | Manually retry failed task |
| `GET` | `/api/tools` | List registered tools and risk levels |
| `GET` | `/api/memory` | Query working and long-term memory |

---

## 🔒 Security & Privacy Architecture

1. **Decoupled Audio Capture**: Wake-word listening operates on a local rolling PCM buffer. Audio recordings are destroyed after command parsing.
2. **Permission Boundary**: High-risk tool calls cannot bypass confirmation. The runtime prompts the WebSocket client and awaits approval before proceeding.
3. **Resource Throttling**: The `ResourceManager` limits CPU/RAM usage. Under high load, non-critical background workers are automatically throttled to preserve system stability.
