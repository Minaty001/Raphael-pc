"""
FastAPI Server for Raphael AI Assistant.
Exposes WebSocket gateway `/ws`, REST API endpoints, and serves JARVIS UI frontend.
Includes Cognitive Brain API routes and modern lifespan management.
"""

import os
import asyncio
import json
import time
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Body, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from raphael.core.configuration import get_config, update_config
from raphael.core.state_manager import get_state_manager
from raphael.core.resource_manager import get_resource_manager
from raphael.core.logging import get_logger
from raphael.network.websocket import get_ws_manager
from raphael.brain.reasoning import get_reasoning_engine
from raphael.brain.llm_router import get_llm_router
from raphael.voice.pipeline import get_voice_pipeline
from raphael.tools.registry import get_tool_registry
from raphael.security.confirmation import get_confirmation_manager
from raphael.memory.long_term import get_long_term_memory
from raphael.memory.working_memory import get_working_memory
from raphael.memory.memory_manager import get_memory_manager
from raphael.memory.user_model import get_user_model
from raphael.core.event_bus import get_event_bus
from raphael.brain.goals import get_goal_engine
from raphael.brain.open_loops import get_open_loop_tracker
from raphael.learning.reflection_engine import get_reflection_engine
from raphael.runtime.always_alive import get_always_alive, RuntimeMode
from raphael.runtime.health_monitor import get_health_monitor
from raphael.runtime.tasks import get_task_manager, TaskPriority, TaskType
from raphael.network.auth import verify_token, require_api_auth

logger = get_logger("network.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    ws_mgr = get_ws_manager()
    ws_mgr.setup_event_listeners()
    logger.info("Raphael FastAPI gateway started with lifespan manager.")
    yield
    logger.info("Raphael FastAPI gateway shutting down.")

app = FastAPI(
    title="Raphael AI Assistant API",
    version="2.0.0",
    description="Raphael Core Gateway & Cognitive Brain API",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    # WebSocket handshakes are rejected by Starlette when allow_origins=["*"]
    # is combined with allow_credentials=True (returns 403). For a localhost
    # assistant we list the explicit origins we serve from. Keep credentials
    # enabled so browser-stored tokens work.
    allow_origins=[
        "http://localhost:8765",
        "http://127.0.0.1:8765",
        "http://localhost:3000",   # Vite dev server (port 3000)
        "http://127.0.0.1:3000",
        "http://localhost:5173",   # Vite dev server (port 5173)
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the static UI. The bundled frontend is now a no-build static site
# (index.html + css/ + src/). The mount is registered at the very END of this
# module (after every /api and /ws route) so the explicit routes take
# precedence and only unmatched paths fall through to the static files.
frontend_static = os.path.abspath("./frontend")


@app.get("/health")
async def health_check():
    state_mgr = get_state_manager()
    return {
        "status": "ok",
        "core": "ok",
        "state": state_mgr.current_state.value,
        "timestamp": time.time()
    }


@app.get("/api/bootstrap")
async def bootstrap_auth(request: Request):
    """Public bootstrap that lets the local UI obtain the API auth token.

    SECURITY MODEL
    --------------
    With the default config (``auth_required=True``) every REST route and the
    WebSocket handshake require the api_token. The token is generated randomly
    on first run and persisted to ``config.override.json``. There is no human
    owner and no password, so the only way the bundled localhost UI can
    authenticate is to read the same token the server is using.

    To avoid exposing the token to the open internet, this endpoint is only
    reachable from a loopback address (127.0.0.1 / ::1 / localhost). Non-local
    clients get 403. The browser client calls this once on startup (no token
    needed), stores the token in localStorage, and attaches it to every
    subsequent WS/REST call via ``wsClient.setToken``.

    This is an honest, local-only handshake — not a real credential system —
    but it does stop *remote* unauthenticated access, which is the threat that
    mattered when auth was previously disabled by default.
    """
    client_ip = request.client.host if request.client else "unknown"
    if client_ip not in ("127.0.0.1", "::1", "localhost"):
        logger.warning(f"/api/bootstrap refused for non-loopback client {client_ip}")
        raise HTTPException(status_code=403, detail="Bootstrap only available from localhost")
    return {"token": get_config().websocket.api_token}


@app.get("/status")
async def status_check():
    state_mgr = get_state_manager()
    res_mgr = get_resource_manager()
    return {
        "state": state_mgr.get_summary(),
        "metrics": res_mgr.get_system_metrics(),
        "effective_mode": res_mgr.get_effective_mode(),
        "timestamp": time.time()
    }

@app.get("/api/config", dependencies=[Depends(require_api_auth)])
async def get_configuration():
    return get_config().to_dict()

@app.get("/api/config/llm", dependencies=[Depends(require_api_auth)])
async def get_llm_config():
    """Return LLM provider settings (no secrets) for the Settings UI."""
    cfg = get_config().llm
    return {
        "primary_provider": cfg.primary_provider,
        "fallback_provider": cfg.fallback_provider,
        "groq_model": cfg.groq_model,
        "groq_free_models": cfg.groq_free_models,
        "ollama_model": cfg.ollama_model,
        "openrouter_model": cfg.openrouter_model,
        "openai_model": cfg.openai_model,
        "providers": ["groq", "ollama", "openrouter", "mock"],
    }

@app.post("/api/config/llm", dependencies=[Depends(require_api_auth)])
async def set_llm_config(payload: Dict[str, Any] = Body(default={})):
    """Set the active LLM provider and/or Groq model. Persists across restarts."""
    allowed_providers = {"groq", "ollama", "openrouter", "mock"}
    updates: Dict[str, Any] = {}
    if "provider" in payload:
        provider = payload["provider"]
        if provider not in allowed_providers:
            raise HTTPException(status_code=400, detail="Invalid provider")
        updates["llm"] = updates.get("llm", {})
        updates["llm"]["primary_provider"] = provider
    if "groq_model" in payload:
        model = payload["groq_model"]
        if model not in get_config().llm.groq_free_models:
            raise HTTPException(status_code=400, detail="Model not in free-models list")
        updates["llm"] = updates.get("llm", {})
        updates["llm"]["groq_model"] = model
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields provided")
    update_config(updates)
    get_config().save_overrides(updates)
    get_llm_router().rebuild()
    return {"ok": True, "primary_provider": get_config().llm.primary_provider,
            "groq_model": get_config().llm.groq_model}

@app.get("/api/tools", dependencies=[Depends(require_api_auth)])
async def list_available_tools():
    return get_tool_registry().list_tools()

@app.post("/api/tools/execute", dependencies=[Depends(require_api_auth)])
async def execute_tool_endpoint(payload: Dict[str, Any] = Body(...)):
    """Run a registered tool synchronously and return its result.

    Body: {"tool": "<name>", "args": {...}}. Reuses the ToolRegistry so the
    tool's own security policy, confirmation flow, and real ActionVerifier
    checks all apply. This is what the frontend Screen / Web Reader panels
    call to exercise read_screen / read_webpage for real (no fake data).
    """
    tool_name = payload.get("tool")
    args = payload.get("args") or {}
    if not tool_name:
        raise HTTPException(status_code=400, detail="`tool` name required")
    reg = get_tool_registry()
    if reg.get_tool(tool_name) is None:
        raise HTTPException(status_code=404, detail=f"Unknown tool '{tool_name}'")
    result = await reg.execute_tool(tool_name, args)
    return result

@app.get("/api/audio/devices", dependencies=[Depends(require_api_auth)])
async def list_audio_devices():
    """List all detected audio input devices and the auto-selected device.

    Returns the device list with transport classification (bluetooth, usb,
    builtin, virtual) and the device currently selected by the priority
    cascade (Bluetooth > USB > Built-in).
    """
    from raphael.voice.device_selector import get_device_selector
    from raphael.voice.microphone import get_microphone
    selector = get_device_selector()
    devices = selector.enumerate_input_devices()
    selected = selector.select_best_device()
    mic = get_microphone()
    return {
        "devices": [
            {
                "index": d.index,
                "name": d.name,
                "kind": d.kind,
                "rate": d.rate,
                "channels": d.max_input_channels,
                "is_default": d.is_default,
            }
            for d in devices
        ],
        "selected": {
            "index": selected.index,
            "name": selected.name,
            "kind": selected.kind,
            "rate": selected.rate,
        } if selected else None,
        "active": {
            "index": mic.current_device.index,
            "name": mic.current_device.name,
            "kind": mic.current_device.kind,
        } if mic.current_device else None,
        "available": selector.available,
    }

@app.get("/api/memories", dependencies=[Depends(require_api_auth)])
async def get_memories():
    return get_long_term_memory().list_memories()

# Cognitive Brain Endpoints
@app.get("/api/brain/context", dependencies=[Depends(require_api_auth)])
async def get_brain_context():
    return get_working_memory().get_summary()

@app.get("/api/brain/user-model", dependencies=[Depends(require_api_auth)])
async def get_brain_user_profile():
    return get_user_model().get_profile()

@app.get("/api/brain/goals", dependencies=[Depends(require_api_auth)])
async def get_brain_goals():
    return get_goal_engine().list_active_goals()

@app.get("/api/brain/open-loops", dependencies=[Depends(require_api_auth)])
async def get_brain_open_loops():
    return get_open_loop_tracker().list_open_loops()

@app.post("/api/brain/forget", dependencies=[Depends(require_api_auth)])
async def forget_memory_endpoint(payload: Dict[str, Any] = Body(...)):
    keyword = payload.get("keyword", "").strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="Keyword parameter required")
    return get_memory_manager().forget_memory(keyword)

@app.post("/api/brain/reflect", dependencies=[Depends(require_api_auth)])
async def trigger_self_reflection(payload: Dict[str, Any] = Body(...)):
    task = payload.get("task", "manual_reflection")
    tool_res = payload.get("tool_result", {"status": "success", "duration_ms": 10})
    return await get_reflection_engine().reflect_on_task(task, tool_res, "Manual API reflection request")

@app.post("/api/confirm", dependencies=[Depends(require_api_auth)])
async def confirm_action(payload: Dict[str, Any] = Body(...)):
    request_id = payload.get("request_id")
    approved = payload.get("approved", False)
    if not request_id:
        raise HTTPException(status_code=400, detail="Missing request_id")
    
    success = get_confirmation_manager().resolve_confirmation(request_id, approved)
    return {"request_id": request_id, "resolved": success, "approved": approved}

@app.post("/api/chat", dependencies=[Depends(require_api_auth)])
async def send_chat_message(payload: Dict[str, Any] = Body(...)):
    text = payload.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text payload required")

    reasoning = get_reasoning_engine()
    res = await reasoning.process_user_input(text)
    return res


@app.post("/api/tts", dependencies=[Depends(require_api_auth)])
async def text_to_speech(payload: Dict[str, Any] = Body(...)):
    """Text-to-speech via Edge TTS. Returns audio/mpeg, or 501 if unavailable."""
    from fastapi.responses import Response
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text required")
    try:
        import io
        import edge_tts
        voice = getattr(get_config().voice, "tts_voice", None) or "en-US-AriaNeural"
        communicate = edge_tts.Communicate(text, voice)
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        audio = buf.getvalue()
        if not audio:
            raise RuntimeError("empty audio")
        return Response(content=audio, media_type="audio/mpeg")
    except Exception as e:
        logger.warning(f"/api/tts unavailable: {e}")
        raise HTTPException(status_code=501, detail="TTS unavailable")

# ---------------------------------------------------------------------------
# Always-Alive Runtime API (Sections 65-71)
# ---------------------------------------------------------------------------
@app.get("/api/runtime/health", dependencies=[Depends(require_api_auth)])
async def runtime_health():
    monitor = get_health_monitor()
    return await monitor.snapshot()

@app.get("/api/runtime/mode", dependencies=[Depends(require_api_auth)])
async def runtime_mode():
    return {"mode": get_always_alive().get_mode()}

@app.post("/api/runtime/mode", dependencies=[Depends(require_api_auth)])
async def set_runtime_mode(payload: Dict[str, Any] = Body(...)):
    mode = payload.get("mode", "NORMAL").upper()
    if mode not in [m.value for m in RuntimeMode]:
        raise HTTPException(status_code=400, detail="Invalid mode")
    await get_always_alive().set_mode(RuntimeMode(mode))
    return {"mode": mode}

@app.post("/api/runtime/interrupt", dependencies=[Depends(require_api_auth)])
async def runtime_interrupt():
    await get_always_alive().interrupt()
    return {"interrupted": True}

@app.get("/api/tasks", dependencies=[Depends(require_api_auth)])
async def list_tasks():
    return get_task_manager().list()

@app.post("/api/tasks", dependencies=[Depends(require_api_auth)])
async def create_task(payload: Dict[str, Any] = Body(...)):
    """Create a background task.

    If the payload carries a `tool` name (one of the registered Tool Registry
    tools), the task actually executes that tool in the background via the
    real executor — not a placeholder. Otherwise it runs a genuine lightweight
    background job (a scheduled notification/reminder) so the task UI reflects
    real work rather than a no-op sleep.
    """
    name = payload.get("name", "Untitled task")
    priority = payload.get("priority", TaskPriority.NORMAL.value)
    task_type = payload.get("type", TaskType.BACKGROUND.value)
    coroutine = _resolve_api_task_coroutine(payload, name, priority)
    tid = get_task_manager().create(
        name=name,
        coroutine=coroutine,
        priority=priority,
        type=task_type,
        max_cpu=payload.get("max_cpu", 25),
        max_memory_mb=payload.get("max_memory_mb", 300),
        estimated_duration_s=payload.get("estimated_duration_s", 0),
    )
    return {"id": tid, "name": name}

def _resolve_api_task_coroutine(payload: Dict[str, Any], name: str, priority: str):
    """Pick a real coroutine for an API-created task (P0 #12).

    Previously all API tasks ran `_noop_task` (just `await asyncio.sleep(2)`),
    so the Task UI never reflected actual work. Now:
      * `tool` present -> execute that registry tool in the background.
      * otherwise -> a genuine reminder/notification background job.
    """
    tool_name = payload.get("tool")
    tool_args = payload.get("args") or {}
    if tool_name:
        async def _run_tool_task(**_kwargs):
            from raphael.tools.registry import get_tool_registry
            reg = get_tool_registry()
            tool = reg.get_tool(tool_name)
            if tool is None:
                raise ValueError(f"Unknown tool '{tool_name}'")
            mgr = get_task_manager()
            task = _kwargs.get("_task")
            result = await tool.execute(user_request=str(tool_args), task_context=task)
            if task is not None:
                task.result = {"tool": tool_name, "output": str(result)[:500]}
                mgr.checkpoint(task.id, task.checkpoint)
        return _run_tool_task

    async def _run_reminder_task(**_kwargs):
        """Real background job: emit a notification after the requested delay."""
        delay = float(payload.get("delay_s", 0) or 0)
        if delay > 0:
            await asyncio.sleep(delay)
        msg = payload.get("message", name)
        await get_event_bus().publish(
            "notification.created",
            {"title": "Background reminder", "message": msg, "priority": priority},
            source="task_engine",
        )
    return _run_reminder_task

@app.post("/api/tasks/{task_id}/pause", dependencies=[Depends(require_api_auth)])
async def pause_task(task_id: str):
    ok = get_task_manager().pause(task_id)
    return {"ok": ok}

@app.post("/api/tasks/{task_id}/resume", dependencies=[Depends(require_api_auth)])
async def resume_task(task_id: str):
    ok = get_task_manager().resume(task_id)
    return {"ok": ok}

@app.post("/api/tasks/{task_id}/cancel", dependencies=[Depends(require_api_auth)])
async def cancel_task(task_id: str):
    ok = get_task_manager().cancel(task_id)
    return {"ok": ok}

@app.post("/api/tasks/{task_id}/retry", dependencies=[Depends(require_api_auth)])
async def retry_task(task_id: str):
    ok = get_task_manager().retry(task_id)
    return {"ok": ok}

async def _noop_task(**kwargs):
    """Default placeholder coroutine for API-created tasks (demo/integration)."""
    await asyncio.sleep(2.0)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Authenticate the WS handshake. Token may be supplied as a query param
    # (?token=...) — for a local-only dev box with auth disabled, loopback
    # connections are still admitted (see network.auth.verify_token).
    client_ip = getattr(websocket.client, "host", None) or "unknown"
    token = websocket.query_params.get("token", "")
    if not verify_token(token, client_ip):
        await websocket.accept()
        await websocket.send_text(json.dumps({"type": "error", "message": "unauthorized"}))
        await websocket.close(code=1008)
        return

    ws_mgr = get_ws_manager()
    await ws_mgr.connect(websocket)

    try:
        while True:
            data_str = await websocket.receive_text()
            try:
                msg = json.loads(data_str)
                msg_type = msg.get("type", "")

                if msg_type == "user.message":
                    text = msg.get("text", "")
                    asyncio.create_task(get_reasoning_engine().process_user_input(text))
                
                elif msg_type == "voice.stt.input":
                    text = msg.get("text", "")
                    is_final = msg.get("is_final", True)
                    asyncio.create_task(get_voice_pipeline().handle_speech_input(text, is_final))

                elif msg_type == "security.confirm_response":
                    req_id = msg.get("request_id")
                    approved = msg.get("approved", False)
                    get_confirmation_manager().resolve_confirmation(req_id, approved)

                elif msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong", "timestamp": time.time()}))

            except json.JSONDecodeError:
                logger.warning(f"Received non-JSON websocket message: {data_str[:100]}")
            except Exception as e:
                logger.error(f"Error handling websocket message: {e}", exc_info=True)

    except WebSocketDisconnect:
        ws_mgr.disconnect(websocket)


# ---------------------------------------------------------------------------
# Static frontend mount — registered LAST so every explicit /api/* and /ws
# route above takes precedence. Only unmatched paths fall through here.
# ---------------------------------------------------------------------------
if os.path.isdir(frontend_static):
    app.mount(
        "/",
        StaticFiles(directory=frontend_static, html=True, check_dir=True),
        name="frontend",
    )
else:
    @app.get("/")
    async def serve_frontend():
        return {
            "message": "Raphael AI Assistant Gateway API is active. Frontend not found."
        }
