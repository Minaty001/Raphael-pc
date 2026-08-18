# 💻 Raphael HUD Frontend

The **Raphael HUD** is a real-time React + Vite desktop interface designed to connect to the persistent **Raphael Always-Alive Runtime** via WebSockets and REST.

---

## 🎨 Key Features & UI Components

### Top Navigation & Global Controls (`src/components/layout/`)
- **`AliveIndicator`**: Live status pill showing WebSocket connection state (`ONLINE` / `OFFLINE`), active runtime mode (`NORMAL`, `FOCUS`, `PAUSE`, `SLEEP`), and background worker counts.
- **`BackgroundTaskDrawer`**: Slide-out drawer displaying running and queued background tasks with progress bars, pause/resume, cancel, and retry controls.
- **`VoiceStatus`**: Real-time privacy indicator reflecting the 9 audio states (e.g. `LISTENING_WAKE`, `RECORDING_COMMAND`, `MUTED`).

### Interactive Panels & Modals (`src/components/`)
- **`RaphaelOrb`**: Dynamic visual orb animating in sync with voice activity, cognition processing, and sleeping states.
- **`CognitiveBrainPanel`**: Live view of current goals, planner sub-tasks, active attention context, and reasoning steps.
- **`ConfirmationModal`**: Security pop-up for approving high-risk tool executions (e.g., shell command execution).
- **`DeveloperConsole`**: Embedded streaming tool output and diagnostic log viewer.

### View Pages (`src/pages/`)
| Page | Route / View | Description |
|---|---|---|
| **Home** | `/` | Main HUD dashboard with Raphael Orb, voice status, and real-time conversation stream. |
| **Memory** | `/memory` | Interactive explorer for working, episodic, semantic, and procedural memory. |
| **Activity** | `/activity` | System audit trail, task execution history, and event logs. |
| **Models** | `/models` | LLM router provider settings (Ollama, Groq, OpenAI, Anthropic). |
| **Goals** | `/goals` | Multi-step user goals and active open loops. |
| **System** | `/system` | CPU/RAM utilization, health status of runtime workers, and system metrics. |
| **Tools** | `/tools` | Tool registry viewer with risk permissions (`READ_ONLY`, `LOW`, `MODERATE`, `HIGH`). |
| **Reminders** | `/reminders` | Active contextual reminders and scheduled alerts. |
| **Developer** | `/developer` | Subsystem diagnostics, API log streams, and command execution tester. |
| **Vision** | `/vision` | Screen perception and visual understanding stream. |
| **Routines** | `/routines` | Scheduled proactive routines and morning briefing configuration. |
| **Settings** | `/settings` | Voice parameters, wake-word sensitivity, runtime mode toggles, and autostart preferences. |

---

## 🛠️ Development & Build Scripts

From the `frontend/` directory:

```bash
# Install dependencies
npm install

# Run dev server with hot reload
npm run dev

# Typecheck and build for production (outputs to dist/)
npm run build

# Preview production build locally
npm run preview
```

---

## 📡 Gateway Integration

The frontend connects to the backend runtime via:
- **WebSocket**: `ws://localhost:8765/ws` (managed by `src/websocket.ts` and `src/stores/raphaelStore.ts`)
- **REST API**: `http://localhost:8765/api`
