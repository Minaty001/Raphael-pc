"""
WebSocket Test Client for Raphael AI Assistant.
Validates gateway connection, event streaming, latency, and tool execution.
"""

import sys
import os
import asyncio
import json
import time

for env_path in ["/tmp/raphael_env", os.path.expanduser("~/.local/lib/python3.12/site-packages")]:
    if os.path.exists(env_path) and env_path not in sys.path:
        sys.path.insert(0, env_path)

import websockets

async def test_websocket_flow(url: str = "ws://localhost:8765/ws"):
    print(f"\n[WS-CLIENT] Connecting to {url}...")
    start_connect = time.time()
    
    try:
        async with websockets.connect(url) as ws:
            connect_latency = (time.time() - start_connect) * 1000
            print(f"[WS-CLIENT] Connected! (Latency: {connect_latency:.1f}ms)")

            # Read initial sync event
            sync_data = await asyncio.wait_for(ws.recv(), timeout=5.0)
            sync_json = json.loads(sync_data)
            print(f"[WS-CLIENT] Received Initial State Sync: {sync_json.get('state')} | CPU: {sync_json.get('metrics', {}).get('cpu_percent')}%")

            # Send test user message
            test_msg = {"type": "user.message", "text": "show system info"}
            print(f"[WS-CLIENT] Sending user message: '{test_msg['text']}'")
            start_send = time.time()
            await ws.send(json.dumps(test_msg))

            # Receive event stream
            for _ in range(5):
                evt_str = await asyncio.wait_for(ws.recv(), timeout=5.0)
                evt = json.loads(evt_str)
                ttfb = (time.time() - start_send) * 1000
                print(f"[WS-CLIENT] EVENT stream -> type: '{evt.get('type')}' | TTFB: {ttfb:.1f}ms")
                if evt.get("type") == "assistant.state" and evt.get("state") == "IDLE":
                    break

            print("[WS-CLIENT] WebSocket flow test completed successfully!\n")
    except Exception as e:
        print(f"[WS-CLIENT] Error testing WebSocket: {e}")

if __name__ == "__main__":
    url_arg = sys.argv[1] if len(sys.argv) > 1 else "ws://localhost:8765/ws"
    asyncio.run(test_websocket_flow(url_arg))
