export type RaphaelStateType =
  | "idle"
  | "listening"
  | "thinking"
  | "executing"
  | "speaking"
  | "error"
  | "offline";

export type PageView =
  | "home"
  | "chat"
  | "memory"
  | "vision"
  | "goals"
  | "routines"
  | "reminders"
  | "activity"
  | "models"
  | "tools"
  | "system"
  | "developer"
  | "settings";

export interface SystemMetrics {
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
  ram_used_mb?: number;
  ram_total_mb?: number;
  uptime_seconds?: number;
  top_processes?: string[];
}

export interface ChatMessage {
  id: string;
  sender: "user" | "raphael" | "system";
  text: string;
  timestamp: number;
  toolResult?: any;
}

export interface ActivityEvent {
  id: string;
  type: string;
  timestamp: string;
  title: string;
  description?: string;
  status?: "running" | "success" | "failed";
}

export interface MemoryRecord {
  id: number;
  subject: string;
  predicate: string;
  object_value: string;
  memory_type: string;
  confidence: number;
  evidence_count: number;
  source?: string;
  created_at: number;
}

export interface GoalItem {
  id: number;
  title: string;
  progress: number;
  priority: number;
  status: string;
  project?: string;
}

export interface RoutineItem {
  id: number;
  name: string;
  pattern: any;
  confidence: number;
  confirmed: boolean;
}

export interface ReminderItem {
  id: number;
  text: string;
  trigger_context?: string;
  due_timestamp?: number;
  status: string;
}

export interface ToolItem {
  name: string;
  description: string;
  risk_level: string;
  parameters: string[];
}

export interface SecurityConfirmationRequest {
  request_id: string;
  tool_name: string;
  args: Record<string, any>;
  reason: string;
  timeout_seconds: number;
}

export interface WSEvent {
  type: string;
  timestamp?: number;
  [key: string]: any;
}

// ---------------------------------------------------------------------------
// Always-Alive Runtime types (Sections 36, 66-71)
// ---------------------------------------------------------------------------

export type AudioStateType =
  | "AUDIO_IDLE"
  | "WAKE_LISTENING"
  | "WAKE_DETECTED"
  | "COMMAND_LISTENING"
  | "PROCESSING"
  | "SPEAKING"
  | "INTERRUPTED"
  | "PAUSED"
  | "ERROR";

export type RuntimeModeType = "NORMAL" | "FOCUS" | "PAUSE" | "SLEEP" | "EXIT";

export type TaskStatusType =
  | "CREATED"
  | "QUEUED"
  | "RUNNING"
  | "PAUSED"
  | "WAITING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";

export type TaskPriorityType =
  | "CRITICAL"
  | "HIGH"
  | "NORMAL"
  | "LOW"
  | "BACKGROUND"
  | "IDLE";

export interface BackgroundTask {
  id: string;
  name: string;
  type: string;
  status: TaskStatusType;
  priority: TaskPriorityType;
  progress: number;
  created_at?: number;
  started_at?: number;
  finished_at?: number;
  error?: string | null;
  max_cpu?: number;
  max_memory_mb?: number;
  dependencies?: string[];
  [key: string]: any;
}

export interface RuntimeHealthComponent {
  status: string;
  detail?: string;
  stale_seconds?: number;
}

export interface RuntimeHealth {
  runtime: string;
  uptime_seconds: number;
  components: Record<string, RuntimeHealthComponent>;
  timestamp: number;
}

export interface RuntimeHeartbeat {
  type: "runtime.heartbeat";
  uptime: number;
  mode: RuntimeModeType;
  workers: number;
  tasks: number;
  voice: string;
  runtime: string;
  components?: Record<string, RuntimeHealthComponent>;
  timestamp?: number;
}
