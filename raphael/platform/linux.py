"""
Linux Platform Adapter for Raphael AI Assistant.
Supports Linux Mint, Ubuntu, and Debian desktop environments.
"""

import os
import sys
import time
import subprocess
import webbrowser
import shutil
from typing import Dict, Any, Optional
from raphael.platform.common import PlatformAdapter, make_action_result
from raphael.core.logging import get_logger

logger = get_logger("platform.linux")

APP_MAP = {
    "chrome": ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"],
    "firefox": ["firefox"],
    "terminal": ["gnome-terminal", "konsole", "xfce4-terminal", "xterm"],
    "calculator": ["gnome-calculator", "kcalc", "galculator"],
    "files": ["nemo", "nautilus", "thunar", "dolphin"],
    "text_editor": ["gedit", "xed", "kate", "mousepad"]
}

class LinuxPlatformAdapter(PlatformAdapter):
    @property
    def os_name(self) -> str:
        return "linux"

    def open_application(self, app_name: str) -> Dict[str, Any]:
        start_time = time.time()
        clean_name = app_name.lower().strip()
        
        candidates = APP_MAP.get(clean_name, [clean_name])
        executed_cmd = None

        for cmd in candidates:
            if shutil.which(cmd):
                try:
                    subprocess.Popen([cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    executed_cmd = cmd
                    break
                except Exception as e:
                    logger.warning(f"Failed to launch candidate {cmd}: {e}")

        duration = (time.time() - start_time) * 1000
        if executed_cmd:
            return make_action_result("open_application", "success", duration, result={"app_name": app_name, "command": executed_cmd})
        else:
            # Fallback to xdg-open or desktop file search
            try:
                subprocess.Popen(["gtk-launch", clean_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return make_action_result("open_application", "success", duration, result={"app_name": app_name, "command": f"gtk-launch {clean_name}"})
            except Exception:
                return make_action_result("open_application", "failed", duration, error=f"Application '{app_name}' not found on system path", retryable=False)

    def close_application(self, app_name: str) -> Dict[str, Any]:
        start_time = time.time()
        clean_name = app_name.lower().strip()
        candidates = APP_MAP.get(clean_name, [clean_name])

        closed = False
        for cmd in candidates:
            try:
                res = subprocess.run(["pkill", "-f", cmd], capture_output=True, text=True)
                if res.returncode == 0:
                    closed = True
                    break
            except Exception as e:
                logger.warning(f"Failed to kill {cmd}: {e}")

        duration = (time.time() - start_time) * 1000
        if closed:
            return make_action_result("close_application", "success", duration, result={"app_name": app_name})
        else:
            return make_action_result("close_application", "failed", duration, error=f"No running process matching '{app_name}'", retryable=False)

    def get_system_metrics(self) -> Dict[str, Any]:
        import psutil
        start_time = time.time()
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=None)
        disk = shutil.disk_usage("/")
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
                "disk_percent": round((disk.used / disk.total) * 100, 1),
                "platform": "linux"
            }
        )

    def set_volume(self, level: int) -> Dict[str, Any]:
        start_time = time.time()
        level = max(0, min(100, level))
        success = False

        if shutil.which("pactl"):
            try:
                subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"], check=True)
                success = True
            except Exception:
                pass

        if not success and shutil.which("amixer"):
            try:
                subprocess.run(["amixer", "set", "Master", f"{level}%"], check=True)
                success = True
            except Exception:
                pass

        duration = (time.time() - start_time) * 1000
        if success:
            return make_action_result("set_volume", "success", duration, result={"volume_level": level})
        else:
            return make_action_result("set_volume", "failed", duration, error="No audio control utility (pactl/amixer) available")

    def get_volume(self) -> Dict[str, Any]:
        start_time = time.time()
        vol = 50
        duration = (time.time() - start_time) * 1000
        return make_action_result("get_volume", "success", duration, result={"volume_level": vol})

    def take_screenshot(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        if not output_path:
            pictures_dir = os.path.expanduser("~/Pictures/Raphael")
            os.makedirs(pictures_dir, exist_ok=True)
            output_path = os.path.join(pictures_dir, f"screenshot_{int(time.time())}.png")

        taken = False
        if shutil.which("scrot"):
            try:
                subprocess.run(["scrot", output_path], check=True)
                taken = True
            except Exception:
                pass
        
        if not taken and shutil.which("gnome-screenshot"):
            try:
                subprocess.run(["gnome-screenshot", "-f", output_path], check=True)
                taken = True
            except Exception:
                pass

        duration = (time.time() - start_time) * 1000
        if taken:
            return make_action_result("take_screenshot", "success", duration, result={"file_path": output_path})
        else:
            return make_action_result("take_screenshot", "failed", duration, error="No screenshot utility found (scrot/gnome-screenshot)")

    def get_clipboard_text(self) -> Dict[str, Any]:
        start_time = time.time()
        text = ""
        if shutil.which("xclip"):
            try:
                res = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True)
                text = res.stdout
            except Exception:
                pass
        duration = (time.time() - start_time) * 1000
        return make_action_result("get_clipboard_text", "success", duration, result={"text": text})

    def set_clipboard_text(self, text: str) -> Dict[str, Any]:
        start_time = time.time()
        if shutil.which("xclip"):
            try:
                p = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE, text=True)
                p.communicate(input=text)
            except Exception:
                pass
        duration = (time.time() - start_time) * 1000
        return make_action_result("set_clipboard_text", "success", duration, result={"length": len(text)})

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
        candidates = APP_MAP.get(clean, [clean])
        try:
            res = subprocess.run(
                ["pgrep", "-f", candidates[0]], capture_output=True, text=True
            )
            return res.returncode == 0 and bool(res.stdout.strip())
        except Exception:
            # Fallback: scan process list via ps
            try:
                res = subprocess.run(
                    ["ps", "-eo", "comm"], capture_output=True, text=True
                )
                procs = [p.strip().lower() for p in res.stdout.splitlines()]
                return any(c in p for c in candidates for p in procs)
            except Exception:
                return False

    def get_foreground_window(self) -> Dict[str, Any]:
        # Best-effort: xdotool gives the active window's PID/name on X11.
        try:
            if shutil.which("xdotool"):
                out = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowpid"],
                    capture_output=True, text=True,
                )
                pid = out.stdout.strip()
                if pid.isdigit():
                    # Resolve the process name from /proc
                    cmdline = ""
                    try:
                        with open(f"/proc/{pid}/comm") as f:
                            cmdline = f.read().strip()
                    except Exception:
                        pass
                    return {"title": None, "app_name": cmdline or None}
        except Exception:
            pass
        return {"title": None, "app_name": None}
