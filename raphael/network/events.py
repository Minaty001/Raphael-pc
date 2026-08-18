"""
Raphael v3 Standard Event Catalog constants.
Defines all official event types for internal Event Bus and WebSocket streaming.
"""

# Connection Lifecycle
EVENT_CONNECTION_OPENED = "connection.opened"
EVENT_CONNECTION_CLOSED = "connection.closed"

# Assistant State & Messages
EVENT_ASSISTANT_STATE = "assistant.state"
EVENT_ASSISTANT_MESSAGE = "assistant.message"
EVENT_ASSISTANT_QUESTION = "assistant.question"
EVENT_ASSISTANT_TOPIC = "assistant.topic"

# Voice System
EVENT_VOICE_WAKE_DETECTED = "voice.wake.detected"
EVENT_VOICE_STT_PARTIAL = "voice.stt.partial"
EVENT_VOICE_STT_FINAL = "voice.stt.final"
EVENT_VOICE_TTS_STARTED = "voice.tts.started"
EVENT_VOICE_TTS_COMPLETED = "voice.tts.completed"

# Perception & Screen
EVENT_SCREEN_CHANGED = "screen.changed"
EVENT_SCREEN_ANALYZED = "screen.analyzed"

# Context & Memory
EVENT_CONTEXT_UPDATED = "context.updated"
EVENT_MEMORY_CREATED = "memory.created"
EVENT_MEMORY_UPDATED = "memory.updated"
EVENT_MEMORY_DELETED = "memory.deleted"
EVENT_MEMORY_CONFLICT = "memory.conflict"

# Brain & Planning
EVENT_INTENT_DETECTED = "intent.detected"
EVENT_PLANNER_STARTED = "planner.started"
EVENT_PLANNER_STEP = "planner.step"
EVENT_PLANNER_COMPLETED = "planner.completed"

# Tools
EVENT_TOOL_STARTED = "tool.started"
EVENT_TOOL_PROGRESS = "tool.progress"
EVENT_TOOL_COMPLETED = "tool.completed"
EVENT_TOOL_FAILED = "tool.failed"

# Learning & Reflection
EVENT_LEARNING_PATTERN = "learning.pattern"
EVENT_LEARNING_SKILL = "learning.skill"
EVENT_LEARNING_LESSON = "learning.lesson"
EVENT_REFLECTION_STARTED = "reflection.started"
EVENT_REFLECTION_COMPLETED = "reflection.completed"

# Goals & Routines & Reminders
EVENT_GOAL_CREATED = "goal.created"
EVENT_GOAL_UPDATED = "goal.updated"
EVENT_GOAL_COMPLETED = "goal.completed"
EVENT_ROUTINE_DETECTED = "routine.detected"
EVENT_REMINDER_CREATED = "reminder.created"
EVENT_REMINDER_TRIGGERED = "reminder.triggered"

# System Metrics & Errors
EVENT_SYSTEM_CPU = "system.cpu"
EVENT_SYSTEM_RAM = "system.ram"
EVENT_SYSTEM_DISK = "system.disk"
EVENT_ERROR = "error"
