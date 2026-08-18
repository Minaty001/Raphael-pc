import React from "react";
import { BackgroundTask, TaskStatusType } from "../../types";
import { X, Pause, Play, Square, RotateCw, Cpu, MemoryStick, Clock } from "lucide-react";

/**
 * BackgroundTaskDrawer — live background task manager (Sections 24, 38, 66).
 * Lists all tasks with status + progress, and exposes Pause / Resume / Cancel /
 * Retry / Details actions. Updates in real time via task.* WS events (Section 70).
 */

const STATUS_META: Record<TaskStatusType, { color: string; icon: string }> = {
  CREATED: { color: "#90a0aa", icon: "•" },
  QUEUED: { color: "#56d9ff", icon: "◷" },
  RUNNING: { color: "#4ce09a", icon: "●" },
  PAUSED: { color: "#f4c95d", icon: "⏸" },
  WAITING: { color: "#6f8cff", icon: "◷" },
  COMPLETED: { color: "#4ce09a", icon: "✓" },
  FAILED: { color: "#ff647c", icon: "✗" },
  CANCELLED: { color: "#90a0aa", icon: "⊘" },
};

const PRIORITY_COLOR: Record<string, string> = {
  CRITICAL: "#ff647c",
  HIGH: "#f4c95d",
  NORMAL: "#56d9ff",
  LOW: "#6f8cff",
  BACKGROUND: "#90a0aa",
  IDLE: "#526372",
};

export const BackgroundTaskDrawer: React.FC<{
  open: boolean;
  onClose: () => void;
  tasks: BackgroundTask[];
  onPause: (id: string) => void;
  onResume: (id: string) => void;
  onCancel: (id: string) => void;
  onRetry: (id: string) => void;
}> = ({ open, onClose, tasks, onPause, onResume, onCancel, onRetry }) => {
  if (!open) return null;

  const active = tasks.filter((t) => ["RUNNING", "QUEUED", "WAITING", "PAUSED"].includes(t.status)).length;

  return (
    <div className="fixed inset-0 z-50 flex justify-end" onClick={onClose}>
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-md h-full bg-[#070c14]/98 border-l border-[var(--border)] flex flex-col font-mono text-xs"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b border-[var(--border)] shrink-0">
          <div>
            <h2 className="font-display text-sm tracking-widest text-[var(--accent-primary)] uppercase">Background Tasks</h2>
            <p className="text-[10px] text-[var(--text-muted)] mt-0.5">{active} active · {tasks.length} total</p>
          </div>
          <button onClick={onClose} className="btn-ghost p-1.5 rounded" title="Close">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {tasks.length === 0 && (
            <div className="text-center text-[var(--text-muted)] italic py-10">
              No background tasks. Raphael runs idle work (memory consolidation, indexing)
              in the background automatically.
            </div>
          )}

          {tasks.map((t) => {
            const meta = STATUS_META[t.status] ?? STATUS_META.CREATED;
            const pColor = PRIORITY_COLOR[t.priority] ?? "#56d9ff";
            const canControl = ["RUNNING", "QUEUED", "WAITING", "PAUSED"].includes(t.status);
            return (
              <div key={t.id} className="hud-card p-3 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span style={{ color: meta.color }}>{meta.icon}</span>
                      <span className="text-[var(--text-primary)] font-semibold truncate">{t.name}</span>
                    </div>
                    <div className="flex items-center gap-2 mt-1 text-[10px] text-[var(--text-muted)]">
                      <span
                        className="px-1.5 py-0.5 rounded uppercase tracking-wider"
                        style={{ color: pColor, border: `1px solid ${pColor}55` }}
                      >
                        {t.priority}
                      </span>
                      <span className="uppercase">{t.status}</span>
                    </div>
                  </div>
                </div>

                {/* Progress bar */}
                {["RUNNING", "PAUSED"].includes(t.status) && (
                  <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${Math.max(0, Math.min(100, t.progress))}%`, background: meta.color }}
                    />
                  </div>
                )}

                {/* Detail row */}
                <div className="flex items-center gap-3 text-[10px] text-[var(--text-muted)]">
                  {typeof t.max_cpu === "number" && (
                    <span className="flex items-center gap-1"><Cpu className="w-3 h-3" />{t.max_cpu}%</span>
                  )}
                  {typeof t.max_memory_mb === "number" && (
                    <span className="flex items-center gap-1"><MemoryStick className="w-3 h-3" />{t.max_memory_mb}MB</span>
                  )}
                  {t.started_at && (
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(t.started_at * 1000).toLocaleTimeString()}
                    </span>
                  )}
                  {t.error && <span className="text-[var(--danger)] truncate">err: {t.error}</span>}
                </div>

                {/* Actions */}
                {canControl && (
                  <div className="flex items-center gap-2 pt-1">
                    {t.status === "PAUSED" ? (
                      <button onClick={() => onResume(t.id)} className="flex items-center gap-1 px-2 py-1 rounded border border-[var(--success)]/40 text-[var(--success)] hover:bg-[var(--success)]/10 text-[10px]">
                        <Play className="w-3 h-3" /> Resume
                      </button>
                    ) : (
                      <button onClick={() => onPause(t.id)} className="flex items-center gap-1 px-2 py-1 rounded border border-[var(--warning)]/40 text-[var(--warning)] hover:bg-[var(--warning)]/10 text-[10px]">
                        <Pause className="w-3 h-3" /> Pause
                      </button>
                    )}
                    <button onClick={() => onCancel(t.id)} className="flex items-center gap-1 px-2 py-1 rounded border border-[var(--danger)]/40 text-[var(--danger)] hover:bg-[var(--danger)]/10 text-[10px]">
                      <Square className="w-3 h-3" /> Cancel
                    </button>
                  </div>
                )}
                {t.status === "FAILED" && (
                  <button onClick={() => onRetry(t.id)} className="flex items-center gap-1 px-2 py-1 rounded border border-[var(--accent-primary)]/40 text-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/10 text-[10px]">
                    <RotateCw className="w-3 h-3" /> Retry
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
