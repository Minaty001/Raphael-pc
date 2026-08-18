"""
Filesystem Tools for Raphael AI Assistant.
"""

import os
import glob
import time
from typing import Dict, Any, List, Optional
from raphael.tools.registry import get_tool_registry
from raphael.security.permissions import RiskLevel
from raphael.platform.common import make_action_result

registry = get_tool_registry()

@registry.register(name="find_file", description="Search files by query pattern in target directory", risk_level=RiskLevel.READ_ONLY)
def find_file(query: str, search_path: Optional[str] = None) -> Dict[str, Any]:
    start_time = time.time()
    search_dir = os.path.expanduser(search_path or "~")
    pattern = os.path.join(search_dir, "**", f"*{query}*")
    matches = glob.glob(pattern, recursive=True)[:25]
    duration = (time.time() - start_time) * 1000

    return make_action_result("find_file", "success", duration, result={"query": query, "matches": matches, "count": len(matches)})

@registry.register(name="read_file", description="Read contents of text file", risk_level=RiskLevel.READ_ONLY)
def read_file(file_path: str, max_chars: int = 4000) -> Dict[str, Any]:
    start_time = time.time()
    abs_path = os.path.expanduser(file_path)
    if not os.path.exists(abs_path):
        duration = (time.time() - start_time) * 1000
        return make_action_result("read_file", "failed", duration, error=f"File not found: '{file_path}'")

    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_chars)
        duration = (time.time() - start_time) * 1000
        return make_action_result("read_file", "success", duration, result={"path": abs_path, "content": content, "size_bytes": os.path.getsize(abs_path)})
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        return make_action_result("read_file", "failed", duration, error=str(e))

@registry.register(name="write_file", description="Write content to file", risk_level=RiskLevel.MODERATE)
def write_file(file_path: str, content: str) -> Dict[str, Any]:
    start_time = time.time()
    abs_path = os.path.expanduser(file_path)
    try:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        duration = (time.time() - start_time) * 1000
        return make_action_result("write_file", "success", duration, result={"path": abs_path, "written_chars": len(content)})
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        return make_action_result("write_file", "failed", duration, error=str(e))

@registry.register(name="create_folder", description="Create new directory", risk_level=RiskLevel.MODERATE)
def create_folder(folder_path: str) -> Dict[str, Any]:
    start_time = time.time()
    abs_path = os.path.expanduser(folder_path)
    try:
        os.makedirs(abs_path, exist_ok=True)
        duration = (time.time() - start_time) * 1000
        return make_action_result("create_folder", "success", duration, result={"path": abs_path})
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        return make_action_result("create_folder", "failed", duration, error=str(e))
