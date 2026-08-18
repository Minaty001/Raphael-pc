"""
Configuration Manager for Raphael AI Assistant.
Supports YAML file configuration and environment variable overrides.
Includes Cognitive Brain & Autonomous Assistant settings.
"""

import os
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional

def get_default_data_dir() -> str:
    user_dir = os.path.expanduser("~/.raphael")
    try:
        os.makedirs(user_dir, exist_ok=True)
        # Test write
        test_file = os.path.join(user_dir, ".write_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return user_dir
    except Exception:
        local_dir = os.path.abspath("./.raphael_data")
        os.makedirs(local_dir, exist_ok=True)
        return local_dir

@dataclass
class AppConfig:
    name: str = "Raphael AI"
    version: str = "2.0.0"
    mode: str = "BALANCED"  # ULTRA_LOW, LOW, BALANCED, PERFORMANCE
    debug: bool = True
    data_dir: str = field(default_factory=get_default_data_dir)

@dataclass
class VoiceConfig:
    wake_word_enabled: bool = True
    wake_phrases: List[str] = field(default_factory=lambda: ["raphael", "hey raphael", "rafeal", "rapheal"])
    sensitivity: float = 0.5
    stt_provider: str = "web"  # web (browser Web Speech), vosk, whisper, mock
    tts_provider: str = "web"  # web (client-side playback), edge, pyttsx3, mock
    vad_enabled: bool = True
    sample_rate: int = 16000

@dataclass
class LLMConfig:
    primary_provider: str = "ollama"  # ollama, openrouter, groq, openai, mock
    fallback_provider: str = "mock"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3:8b"
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct"
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = "llama-3.3-70b-versatile"
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = "gpt-4o-mini"
    max_tokens: int = 1024
    temperature: float = 0.7

@dataclass
class MemoryConfig:
    sqlite_db_path: str = ""
    enable_vector_store: bool = True
    vector_dim: int = 384
    short_term_max_messages: int = 20
    memory_mode: str = "SELECTIVE"  # NONE, SESSION_ONLY, SELECTIVE, FULL_PERSONAL_MEMORY
    importance_threshold: float = 0.6

    def __post_init__(self):
        if not self.sqlite_db_path:
            self.sqlite_db_path = os.path.join(get_default_data_dir(), "memory.db")

@dataclass
class ScreenConfig:
    mode: str = "ON_DEMAND"  # OFF, ON_DEMAND, SMART_CONTEXT, CONTINUOUS
    enable_ocr: bool = True
    capture_interval_seconds: int = 10
    save_screenshots: bool = False

@dataclass
class ProactiveConfig:
    enabled: bool = True
    max_interruptions_per_hour: int = 2
    autonomy_level: int = 2  # Level 0 (Chat) to Level 5 (High Autonomy)

@dataclass
class RuntimeConfig:
    """Always-Alive runtime behavior (Sections 1-4, 49-53, 73)."""
    background_mode_enabled: bool = True
    keep_alive_on_window_close: bool = True
    keep_wake_listener_active: bool = True
    continue_background_tasks: bool = True
    continue_reminders: bool = True
    continue_memory_maintenance: bool = True
    startup_mode: str = "MINIMIZED"  # OFF, ON, MINIMIZED
    heartbeat_interval_seconds: int = 5
    # Focus / Sleep / Pause defaults
    default_mode: str = "NORMAL"  # NORMAL | FOCUS | PAUSE | SLEEP

@dataclass
class BackgroundConfig:
    """Background Task Engine tuning (Sections 21-22, 48)."""
    pool_size_override: int = 0  # 0 = auto from resource mode
    enable_checkpointing: bool = True
    enable_persistence: bool = True
    # Resource policy thresholds (Section 48)
    ram_pause_noncritical_pct: int = 90
    ram_reduce_workers_pct: int = 80
    cpu_throttle_pct: int = 85

@dataclass
class WakeWordConfig:
    """Wake-word + voice background behavior (Sections 11-16, 34-35)."""
    rolling_buffer_seconds: float = 1.0  # Section 13
    conversational_window_seconds: int = 8  # Section 15
    strip_wake_phrase: bool = True  # Section 14
    privacy_indicators: bool = True  # Section 35

@dataclass
class LearningConfig:
    enabled: bool = True
    adaptive: bool = True
    auto_commit_threshold: float = 0.85

@dataclass
class CuriosityConfig:
    enabled: bool = True
    max_questions_per_hour: int = 2

@dataclass
class WebSocketConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    auth_required: bool = False  # Trusted for localhost by default
    api_token: str = "raphael_secret_token"

@dataclass
class SecurityConfig:
    require_confirmation_for_high_risk: bool = True
    confirm_timeout_seconds: int = 30
    allowed_commands: List[str] = field(default_factory=lambda: [
        "python", "python3", "git", "ls", "dir", "cat", "echo", "whoami", "uname", "uptime", "ps", "top"
    ])
    dangerous_keywords: List[str] = field(default_factory=lambda: [
        "rm -rf", "format", "mkfs", "dd if=", "> /dev/sd", "drop database", "shutdown", "reboot", "del /f /s /q"
    ])

@dataclass
class RaphaelConfig:
    app: AppConfig = field(default_factory=AppConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    screen: ScreenConfig = field(default_factory=ScreenConfig)
    proactive: ProactiveConfig = field(default_factory=ProactiveConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    background: BackgroundConfig = field(default_factory=BackgroundConfig)
    wakeword: WakeWordConfig = field(default_factory=WakeWordConfig)
    learning: LearningConfig = field(default_factory=LearningConfig)
    curiosity: CuriosityConfig = field(default_factory=CuriosityConfig)
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)

    def get_data_dir(self) -> str:
        return self.app.data_dir

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def load_defaults(cls) -> "RaphaelConfig":
        config = cls()
        os.makedirs(config.app.data_dir, exist_ok=True)
        return config

_current_config: Optional[RaphaelConfig] = None

def get_config() -> RaphaelConfig:
    global _current_config
    if _current_config is None:
        _current_config = RaphaelConfig.load_defaults()
    return _current_config

def update_config(updates: Dict[str, Any]) -> RaphaelConfig:
    global _current_config
    cfg = get_config()
    for key, val in updates.items():
        if hasattr(cfg, key):
            sub_obj = getattr(cfg, key)
            if isinstance(val, dict) and hasattr(sub_obj, "__dict__"):
                for sub_k, sub_v in val.items():
                    if hasattr(sub_obj, sub_k):
                        setattr(sub_obj, sub_k, sub_v)
            else:
                setattr(cfg, key, val)
    return cfg
