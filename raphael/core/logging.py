"""
Structured Logger for Raphael AI Assistant.
Supports separate log channels (application, voice, tool, websocket, security).
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict
from raphael.core.configuration import get_default_data_dir

_loggers: Dict[str, logging.Logger] = {}

def get_logger(name: str = "application") -> logging.Logger:
    global _loggers
    if name in _loggers:
        return _loggers[name]

    log_dir = os.path.join(get_default_data_dir(), "logs")
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(f"raphael.{name}")
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers
    if not logger.handlers:
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # File Handler
        file_path = os.path.join(log_dir, f"{name}.log")
        file_handler = RotatingFileHandler(
            file_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

    _loggers[name] = logger
    return logger
