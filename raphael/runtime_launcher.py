#!/usr/bin/env python3
"""
raphael-runtime — dedicated background process for Raphael v3 (Sections 3-4, 73).

Runs the Always-Alive Runtime + WebSocket gateway in a single process. The UI
(frontend) is a *client* that connects via WebSocket; closing it never stops this
process. Suitable for launching from systemd --user, a desktop autostart entry,
or a tray launcher.

Design:
  * A dedicated asyncio event loop runs the persistent runtime (perception loop,
    wake listener, background task engine, health watchdog, heartbeat).
  * uvicorn (the WS/REST gateway) runs on the same loop via uvicorn.Server,
    so the UI can connect while the runtime stays alive independently of the UI.
"""

import sys
import os
import asyncio
import signal
import argparse

# Ensure local + env site-packages are importable.
for env_path in ["/tmp/raphael_env", os.path.expanduser("~/.local/lib/python3.12/site-packages")]:
    if os.path.exists(env_path) and env_path not in sys.path:
        sys.path.insert(0, env_path)

from raphael.core.configuration import get_config
from raphael.core.logging import get_logger
from raphael.core.runtime import get_runtime

logger = get_logger("raphael_runtime")


async def _main_async():
    config = get_config()
    host = config.websocket.host
    port = config.websocket.port

    logger.info("=== RAPHAEL RUNTIME PROCESS STARTING ===")

    # Boot the always-alive runtime (starts its own background workers).
    runtime = get_runtime()
    await runtime.start()

    # Start the WebSocket/REST gateway on the same loop.
    import uvicorn
    from raphael.network.api import app

    server = uvicorn.Server(
        uvicorn.Config(app, host=host, port=port, log_level="info", reload=False)
    )

    # Graceful shutdown on SIGINT/SIGTERM (Section 52).
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _request_stop():
        logger.info("Shutdown signal received.")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop)
        except NotImplementedError:
            pass  # Windows

    logger.info("=== RAPHAEL ALWAYS-ALIVE AND GATEWAY READY ===")
    await server.serve()
    await stop_event.wait()
    await runtime.stop()
    logger.info("Raphael runtime process exited cleanly.")


def main():
    parser = argparse.ArgumentParser(description="Raphael v3 Always-Alive Runtime")
    parser.add_argument("--host", default=None, help="WebSocket host override")
    parser.add_argument("--port", type=int, default=None, help="WebSocket port override")
    args = parser.parse_args()

    if args.host:
        os.environ["RAPHAEL_WS_HOST"] = args.host
    if args.port:
        os.environ["RAPHAEL_WS_PORT"] = str(args.port)

    try:
        asyncio.run(_main_async())
    except KeyboardInterrupt:
        logger.info("Interrupted; exiting.")


if __name__ == "__main__":
    main()
