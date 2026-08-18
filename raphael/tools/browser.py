"""
Browser & Web Tools for Raphael AI Assistant.
"""

import time
import urllib.parse
from typing import Dict, Any
from raphael.tools.registry import get_tool_registry
from raphael.security.permissions import RiskLevel
from raphael.platform.factory import get_platform_adapter
from raphael.platform.common import make_action_result

registry = get_tool_registry()

@registry.register(name="launch_url", description="Open URL in web browser", risk_level=RiskLevel.LOW_RISK)
def launch_url(url: str) -> Dict[str, Any]:
    adapter = get_platform_adapter()
    return adapter.launch_browser(url)

@registry.register(name="search_web", description="Perform web search for query string", risk_level=RiskLevel.LOW_RISK)
def search_web(query: str) -> Dict[str, Any]:
    start_time = time.time()
    encoded = urllib.parse.quote_plus(query)
    search_url = f"https://www.google.com/search?q={encoded}"
    adapter = get_platform_adapter()
    res = adapter.launch_browser(search_url)
    duration = (time.time() - start_time) * 1000
    
    if res.get("status") == "success":
        return make_action_result("search_web", "success", duration, result={"query": query, "url": search_url})
    else:
        return make_action_result("search_web", "failed", duration, error=res.get("error", "Failed to launch browser for search"))
