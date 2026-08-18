"""
CLI Entry point for Raphael AI Assistant.
Commands:
  server   - Start the Raphael server and WebSocket gateway
  test     - Run the automated test suite
  doctor   - Perform system diagnostics and dependency checks
"""

import sys
import os
import argparse
import asyncio

# Ensure dependencies installed in /tmp/raphael_env or local env are in sys.path
for env_path in ["/tmp/raphael_env", os.path.expanduser("~/.local/lib/python3.12/site-packages")]:
    if os.path.exists(env_path) and env_path not in sys.path:
        sys.path.insert(0, env_path)

from raphael.core.configuration import get_config
from raphael.core.logging import get_logger

logger = get_logger("cli")

def run_server():
    import uvicorn
    from raphael.core.runtime import get_runtime

    config = get_config()
    host = config.websocket.host
    port = config.websocket.port

    logger.info(f"Starting Raphael Server on http://{host}:{port}")

    # The runtime runs an infinite perception loop, so we boot it in a dedicated
    # daemon thread with its own event loop. This cleanly separates the persistent
    # "Raphael runtime" from the WebSocket UI gateway (uvicorn) per Sections 3-4:
    # the runtime is the assistant; the UI is only a client. Closing the UI never
    # terminates the runtime.
    runtime = get_runtime()

    def _boot_in_loop():
        import asyncio as _asyncio
        loop = _asyncio.new_event_loop()

        async def _runner():
            try:
                await runtime.start()
            except Exception as e:
                logger.error(f"Runtime boot failed: {e}", exc_info=True)

        loop.run_until_complete(_runner())

    boot_thread = threading.Thread(target=_boot_in_loop, name="raphael-runtime", daemon=True)
    boot_thread.start()

    uvicorn.run("raphael.network.api:app", host=host, port=port, log_level="info", reload=False)

def run_doctor():
    print("\n" + "="*50)
    print("      RAPHAEL AI ASSISTANT DIAGNOSTIC SYSTEM      ")
    print("="*50 + "\n")

    checks = []

    # 1. Python Environment
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    checks.append(("✓", f"Python Environment ({py_ver})"))

    # 2. Platform Adapter
    try:
        from raphael.platform.factory import get_platform_adapter
        adapter = get_platform_adapter()
        checks.append(("✓", f"Platform Adapter ({adapter.os_name})"))
    except Exception as e:
        checks.append(("✗", f"Platform Adapter ({e})"))

    # 3. Core Dependencies
    for pkg in ["fastapi", "uvicorn", "pydantic", "websockets", "psutil"]:
        try:
            __import__(pkg)
            checks.append(("✓", f"Dependency: {pkg}"))
        except ImportError:
            checks.append(("✗", f"Dependency: {pkg} (missing)"))

    # 4. Tool Registry
    try:
        import raphael.tools.system
        import raphael.tools.applications
        import raphael.tools.filesystem
        import raphael.tools.browser
        import raphael.tools.developer
        import raphael.tools.media
        from raphael.tools.registry import get_tool_registry
        tools = get_tool_registry().list_tools()
        checks.append(("✓", f"Tool Registry ({len(tools)} tools loaded)"))
    except Exception as e:
        checks.append(("✗", f"Tool Registry ({e})"))

    # 5. SQLite Memory DB
    try:
        from raphael.memory.long_term import get_long_term_memory
        mem = get_long_term_memory()
        checks.append(("✓", f"Database (SQLite memory ready at {mem.db_path})"))
    except Exception as e:
        checks.append(("✗", f"Database ({e})"))

    # 6. LLM Router / Ollama check
    try:
        from raphael.brain.llm_router import get_llm_router
        router = get_llm_router()
        name, provider = asyncio.run(router.get_active_provider())
        checks.append(("✓", f"LLM Router (Active provider: {name})"))
    except Exception as e:
        checks.append(("✗", f"LLM Router ({e})"))

    for status, desc in checks:
        print(f" {status} {desc}")

    print("\n" + "="*50)
    print("Diagnostics complete.")
    print("="*50 + "\n")

def run_tests():
    import pytest
    print("Running Raphael Test Suite...")
    ret = pytest.main(["-v", "tests"])
    sys.exit(ret)

def main():
    parser = argparse.ArgumentParser(description="Raphael AI Assistant CLI")
    parser.add_argument("command", choices=["server", "test", "doctor"], help="Command to execute")
    args = parser.parse_args()

    if args.command == "server":
        run_server()
    elif args.command == "doctor":
        run_doctor()
    elif args.command == "test":
        run_tests()

if __name__ == "__main__":
    main()
