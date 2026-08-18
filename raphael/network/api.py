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
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from raphael.core.configuration import get_config
from raphael.core.state_manager import get_state_manager
from raphael.core.resource_manager import get_resource_manager
from raphael.core.logging import get_logger
from raphael.network.websocket import get_ws_manager
from raphael.brain.reasoning import get_reasoning_engine
from raphael.voice.pipeline import get_voice_pipeline
from raphael.tools.registry import get_tool_registry
from raphael.security.confirmation import get_confirmation_manager
from raphael.memory.long_term import get_long_term_memory
from raphael.memory.working_memory import get_working_memory
from raphael.memory.memory_manager import get_memory_manager
from raphael.memory.user_model import get_user_model
from raphael.brain.goals import get_goal_engine
from raphael.brain.open_loops import get_open_loop_tracker
from raphael.learning.reflection_engine import get_reflection_engine

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dist = os.path.abspath("./frontend/dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

@app.get("/")
async def serve_frontend():
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Raphael AI Assistant Gateway API is active. JARVIS UI build not found."}

@app.get("/health")
async def health_check():
    state_mgr = get_state_manager()
    return {
        "status": "ok",
        "core": "ok",
        "state": state_mgr.current_state.value,
        "timestamp": time.time()
    }

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

@app.get("/api/config")
async def get_configuration():
    return get_config().to_dict()

@app.get("/api/tools")
async def list_available_tools():
    return get_tool_registry().list_tools()

@app.get("/api/memories")
async def get_memories():
    return get_long_term_memory().list_memories()

# Cognitive Brain Endpoints
@app.get("/api/brain/context")
async def get_brain_context():
    return get_working_memory().get_summary()

@app.get("/api/brain/user-model")
async def get_brain_user_profile():
    return get_user_model().get_profile()

@app.get("/api/brain/goals")
async def get_brain_goals():
    return get_goal_engine().list_active_goals()

@app.get("/api/brain/open-loops")
async def get_brain_open_loops():
    return get_open_loop_tracker().list_open_loops()

@app.post("/api/brain/forget")
async def forget_memory_endpoint(payload: Dict[str, Any] = Body(...)):
    keyword = payload.get("keyword", "").strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="Keyword parameter required")
    return get_memory_manager().forget_memory(keyword)

@app.post("/api/brain/reflect")
async def trigger_self_reflection(payload: Dict[str, Any] = Body(...)):
    task = payload.get("task", "manual_reflection")
    tool_res = payload.get("tool_result", {"status": "success", "duration_ms": 10})
    return await get_reflection_engine().reflect_on_task(task, tool_res, "Manual API reflection request")

@app.post("/api/confirm")
async def confirm_action(payload: Dict[str, Any] = Body(...)):
    request_id = payload.get("request_id")
    approved = payload.get("approved", False)
    if not request_id:
        raise HTTPException(status_code=400, detail="Missing request_id")
    
    success = get_confirmation_manager().resolve_confirmation(request_id, approved)
    return {"request_id": request_id, "resolved": success, "approved": approved}

@app.post("/api/chat")
async def send_chat_message(payload: Dict[str, Any] = Body(...)):
    text = payload.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text payload required")

    reasoning = get_reasoning_engine()
    res = await reasoning.process_user_input(text)
    return res

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
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
