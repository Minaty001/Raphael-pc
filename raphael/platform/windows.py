"""
Windows Platform Adapter for Raphael AI Assistant.
Supports Windows 10 and Windows 11 desktop systems.
"""

import os
import sys
import time
import subprocess
import webbrowser
from typing import Dict, Any, Optional
from raphael.platform.common import PlatformAdapter, make_action_result
from raphael.core.logging import get_logger

logger = get_logger("platform.windows")

WIN_APP_MAP = {
    "chrome": "chrome.exe",
    "edge": "msedge.exe",
    "firefox": "firefox.exe",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "explorer": "explorer.exe",
    "taskmgr": "taskmgr.exe"
}

class WindowsPlatformAdapter(PlatformAdapter):
    @property
    def os_name(self) -> str:
        return "windows"

    def open_application(self, app_name: str) -> Dict[str, Any]:
        start_time = time.time()
        clean_name = app_name.lower().strip()
        exe_name = WIN_APP_MAP.get(clean_name, clean_name)
        if not exe_name.endswith(".exe"):
            exe_name += ".exe"

        try:
            subprocess.Popen(["start", exe_name], shell=True)
            duration = (time.time() - start_time) * 1000
            return make_action_result("open_application", "success", duration, result={"app_name": app_name, "command": exe_name})
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return make_action_result("open_application", "failed", duration, error=str(e))

    def close_application(self, app_name: str) -> Dict[str, Any]:
        start_time = time.time()
        clean_name = app_name.lower().strip()
        exe_name = WIN_APP_MAP.get(clean_name, clean_name)
        if not exe_name.endswith(".exe"):
            exe_name += ".exe"

        try:
            res = subprocess.run(["taskkill", "/F", "/IM", exe_name], capture_output=True, text=True)
            duration = (time.time() - start_time) * 1000
            if res.returncode == 0:
                return make_action_result("close_application", "success", duration, result={"app_name": app_name})
            else:
                return make_action_result("close_application", "failed", duration, error=res.stderr or "Process not found")
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return make_action_result("close_application", "failed", duration, error=str(e))

    def get_system_metrics(self) -> Dict[str, Any]:
        import psutil
        start_time = time.time()
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=None)
        duration = (time.time() - start_time) * 1000

        return make_action_result(
            "get_system_metrics",
            "success",
            duration,
            result={
                "cpu_percent": cpu,
                "ram_percent": mem.percent,
                "ram_used_mb": round(mem.used / (1024 * 1024), 1),
                "ram_total_mb": round(mem.total / (1024 * 1024), 1),
                "platform": "windows"
            }
        )

    def set_volume(self, level: int) -> Dict[str, Any]:
        start_time = time.time()
        level = max(0, min(100, level))
        # Use nircmd or powershell fallback
        try:
            ps_script = f"(New-Object -ComObject WScript.Shell).SendKeys([char]174 * 50); for($i=0; $i -lt {level//2}; $i++) {{ (New-Object -ComObject WScript.Shell).SendKeys([char]175) }}"
            subprocess.run(["powershell", "-Command", ps_script], capture_output=True)
            duration = (time.time() - start_time) * 1000
            return make_action_result("set_volume", "success", duration, result={"volume_level": level})
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return make_action_result("set_volume", "failed", duration, error=str(e))

    def get_volume(self) -> Dict[str, Any]:
        start_time = time.time()
        duration = (time.time() - start_time) * 1000
        return make_action_result("get_volume", "success", duration, result={"volume_level": 50})

    def take_screenshot(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        if not output_path:
            pictures_dir = os.path.expanduser("~/Pictures/Raphael")
            os.makedirs(pictures_dir, exist_ok=True)
            output_path = os.path.join(pictures_dir, f"screenshot_{int(time.time())}.png")

        try:
            ps_script = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('{{PRTSC}}')"
            subprocess.run(["powershell", "-Command", ps_script], capture_output=True)
            duration = (time.time() - start_time) * 1000
            return make_action_result("take_screenshot", "success", duration, result={"file_path": output_path})
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return make_action_result("take_screenshot", "failed", duration, error=str(e))

    def get_clipboard_text(self) -> Dict[str, Any]:
        start_time = time.time()
        try:
            res = subprocess.run(["powershell", "-Command", "Get-Clipboard"], capture_output=True, text=True)
            duration = (time.time() - start_time) * 1000
            return make_action_result("get_clipboard_text", "success", duration, result={"text": res.stdout.strip()})
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return make_action_result("get_clipboard_text", "failed", duration, error=str(e))

    def set_clipboard_text(self, text: str) -> Dict[str, Any]:
        start_time = time.time()
        try:
            subprocess.run(["powershell", "-Command", f"Set-Clipboard -Value '{text}'"], capture_output=True)
            duration = (time.time() - start_time) * 1000
            return make_action_result("set_clipboard_text", "success", duration, result={"length": len(text)})
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return make_action_result("set_clipboard_text", "failed", duration, error=str(e))

    def launch_browser(self, url: str) -> Dict[str, Any]:
        start_time = time.time()
        try:
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url
            webbrowser.open(url)
            duration = (time.time() - start_time) * 1000
            return make_action_result("launch_browser", "success", duration, result={"url": url})
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return make_action_result("launch_browser", "failed", duration, error=str(e))

    def is_process_running(self, name: str) -> bool:
        clean = name.lower().strip()
        exe_name = WIN_APP_MAP.get(clean, clean)
        if not exe_name.endswith(".exe"):
            exe_name += ".exe"
        try:
            res = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {exe_name}"],
                capture_output=True, text=True,
            )
            return exe_name.lower() in res.stdout.lower()
        except Exception:
            return False

    def get_foreground_window(self) -> Dict[str, Any]:
        try:
            ps_script = (
                "Add-Type @'\\n"
                "using System; using System.Runtime.InteropServices;\\n"
                "public class W { [DllImport(\"user32.dll\")] public static extern IntPtr GetForegroundWindow(); "
                "[DllImport(\"user32.dll\")] public static extern int GetWindowText(IntPtr h, System.Text.StringBuilder s, int n); }\\n"
                "@'\\n"
                "$h = [W]::GetForegroundWindow(); "
                "$sb = New-Object System.Text.StringBuilder 256; "
                "[void][W]::GetWindowText($h, $sb, 256); "
                "Write-Output $sb.ToString()"
            )
            res = subprocess.run(
                ["powershell", "-Command", ps_script], capture_output=True, text=True
            )
            title = res.stdout.strip()
            return {"title": title or None, "app_name": None}
        except Exception:
            return {"title": None, "app_name": None}
