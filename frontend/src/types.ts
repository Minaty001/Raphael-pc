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
