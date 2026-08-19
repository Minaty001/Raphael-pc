# 💻 Raphael HUD Frontend

The **Raphael HUD** is a real-time desktop interface for the persistent
**Raphael Always-Alive Runtime**. It connects over WebSockets and REST and is
served by the backend itself — **no build step, no framework**. It is plain
HTML + CSS + vanilla JS so it runs as static files mounted by
`raphael/network/api.py` (`StaticFiles(directory=frontend, html=True)`).

---

## 📁 Layout

```
frontend/
├── index.html              # single page: header, halo canvas, response area, input, settings
├── css/style.css           # design tokens (CSS variables) + all UI styling
└── src/
    ├── services/api.js     # window.RaphaelApi — REST + WS + token bootstrap (loaded first)
    └── app.js              # RaphaelApp — UI state, halo/particle canvas, event handling
```

There is **no** `npm install`, `vite`, `tsc`, or `dist/`. Edit the files
directly; the backend serves them as-is.

---

## 🎨 What's on screen

- **Halo canvas** (`#halo-canvas`) — a procedurally-drawn animated orb whose
  colour and motion reflect the assistant state (`WAKING` / `IDLE` /
  `LISTENING` / `THINKING` / `SPEAKING` / `ERROR`). Tap it to toggle listening.
- **Status label** — the current state, colour-coded.
- **Response area** — the assistant's text reply, plus a live **actions list**
  of tool calls (`tool.started` → `RUN`, `tool.completed` → `DONE`/`FAIL`)
  rendered update-in-place (no duplicate badges).
- **Input area** — type a message, or use the mic button / Spacebar to speak
  (browser `SpeechRecognition`).
- **Settings** (gear icon) — set the WebSocket/Server URL (defaults to the
  local gateway). Saved to `localStorage`.

---

## 🔐 Gateway integration

The frontend talks to the backend runtime via:

- **WebSocket**: `ws://localhost:8765/ws?token=<api_token>` — the token is
  bootstrapped once from the loopback-only `/api/bootstrap` endpoint and cached
  in `localStorage` (see `src/services/api.js`).
- **REST API**: `http://localhost:8765/api/*` (all gated by the same token,
  except `/health`, `/status`, and `/api/bootstrap`).

The WebSocket is **auth-gated**; the HUD fetches the token before opening the
connection.

---

## ▶️ Running it

The UI ships with the backend. Start the runtime:

```bash
cd /home/saif/Desktop/Raphael-pc
source venv/bin/activate
python -m uvicorn raphael.network.api:app --host 127.0.0.1 --port 8765
```

Then open `http://localhost:8765/` in a browser (Chrome/Edge recommended for
`SpeechRecognition`). No separate frontend dev server is required.

---

## ♿ Accessibility / performance notes

- Honours `prefers-reduced-motion: reduce` — renders a single static halo frame
  instead of animating.
- Pauses the halo + particle `requestAnimationFrame` loops when the tab is
  hidden (resumes on focus) to avoid needless CPU/battery drain.
- Tool names/args are rendered with `textContent` (never `innerHTML`), so
  backend-supplied values cannot inject markup.
