import React from "react";
import { RuntimeHealth, RuntimeHeartbeat, RuntimeModeType } from "../../types";
import { X, Cpu, MemoryStick, Activity, Mic, Wifi, Brain, Settings, Zap } from "lucide-react";

/**
 * RuntimePanel — Always-Alive runtime health drawer (Sections 37, 67, 69).
 * Shows uptime, workers, tasks, voice, memory, websocket, CPU/RAM and lets the
 * user switch runtime modes (NORMAL / FOCUS / PAUSE / SLEEP / EXIT).
 */

const MODES: RuntimeModeType[] = ["NORMAL", "FOCUS", "PAUSE", "SLEEP"];

const COMPONENT_ICON: Record<string, React.ReactNode> = {
  core: <Activity className="w-3.5 h-3.5" />,
  voice: <Mic className="w-3.5 h-3.5" />,
  wakeword: <Mic className="w-3.5 h-3.5" />,
  scheduler: <Zap className="w-3.5 h-3.5" />,
  memory: <Brain className="w-3.5 h-3.5" />,
  websocket: <Wifi className="w-3.5 h-3.5" />,
  llm: <Settings className="w-3.5 h-3.5" />,
  tasks: <Zap className="w-3.5 h-3.5" />,
};

const STATUS_COLOR: Record<string, string> = {
  ok: "text-[var(--success)]",
  ready: "text-[var(--success)]",
  alive: "text-[var(--success)]",
  running: "text-[var(--success)]",
  available: "text-[var(--success)]",
  healthy: "text-[var(--success)]",
  connected: "text-[var(--success)]",
  error: "text-[var(--danger)]",
  paused: "text-[var(--warning)]",
};

const fmtUptime = (s: number) => {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = Math.floor(s % 60);
  return `${h}h ${m}m ${sec}s`;
};

export const RuntimePanel: React.FC<{
  open: boolean;
  onClose: () => void;
  health: RuntimeHealth | null;
  heartbeat: RuntimeHeartbeat | null;
  runtimeMode: RuntimeModeType;
  onSetMode: (m: RuntimeModeType) => void;
  onInterrupt: () => void;
}> = ({ open, onClose, health, heartbeat, runtimeMode, onSetMode, onInterrupt }) => {
  if (!open) return null;

  const components = health?.components ?? {};
  const uptime = heartbeat?.uptime ?? health?.uptime_seconds ?? 0;
  const workers = heartbeat?.workers ?? 0;
  const tasks = heartbeat?.tasks ?? 0;

  return (
    <div className="fixed inset-0 z-50 flex justify-end" onClick={onClose}>
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-md h-full bg-[#070c14]/98 border-l border-[var(--border)] p-5 overflow-y-auto font-mono text-xs"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-[var(--border)] pb-3 mb-4">
          <h2 className="font-display text-sm tracking-widest text-[var(--accent-primary)] uppercase">Runtime</h2>
          <button onClick={onClose} className="btn-ghost p-1.5 rounded" title="Close">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Aliveness summary */}
        <div className="hud-card p-4 mb-4 space-y-2">
          <div className="flex items-center gap-2">
            <span
              className={`w-3 h-3 rounded-full ${
                health?.runtime === "alive" ? "bg-[var(--success)] shadow-[0_0_10px_var(--success)] animate-pulse" : "bg-[var(--danger)]"
              }`}
            />
            <span className="font-display text-base tracking-widest text-[var(--success)] uppercase">
              RAPHAEL ALIVE
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-[11px] text-[var(--text-secondary)]">
            <div>Uptime: <span className="text-white">{fmtUptime(uptime)}</span></div>
            <div>Workers: <span className="text-white">{workers}</span></div>
            <div>Tasks: <span className="text-white">{tasks}</span></div>
            <div>Mode: <span className="text-[var(--warning)]">{runtimeMode}</span></div>
          </div>
        </div>

        {/* Component health grid */}
        <div className="mb-4">
          <div className="text-[10px] font-mono uppercase tracking-widest text-[var(--text-muted)] mb-2">
            Component Health
          </div>
          <div className="space-y-1.5">
            {Object.entries(components).map(([name, info]) => (
              <div key={name} className="flex items-center justify-between bg-[var(--bg-secondary)] border border-[var(--border)] rounded px-3 py-2">
                <div className="flex items-center gap-2 text-[var(--text-secondary)]">
                  {COMPONENT_ICON[name] ?? <Activity className="w-3.5 h-3.5" />}
                  <span className="capitalize">{name}</span>
                </div>
                <span className={`uppercase ${STATUS_COLOR[info.status] ?? "text-[var(--text-secondary)]"}`}>
                  {info.status}
                </span>
              </div>
            ))}
            {Object.keys(components).length === 0 && (
              <div className="text-[var(--text-muted)] italic px-2">No health data yet — connect to runtime.</div>
            )}
          </div>
        </div>

        {/* Mode controls (Sections 49-52) */}
        <div className="mb-4">
          <div className="text-[10px] font-mono uppercase tracking-widest text-[var(--text-muted)] mb-2">
            Runtime Mode
          </div>
          <div className="grid grid-cols-2 gap-2">
            {MODES.map((m) => (
              <button
                key={m}
                onClick={() => onSetMode(m)}
                className={`px-3 py-2 rounded border font-mono text-[11px] uppercase tracking-wider transition-all ${
                  runtimeMode === m
                    ? "bg-[var(--accent-primary)]/20 border-[var(--accent-primary)]/50 text-[var(--accent-primary)]"
                    : "bg-[var(--bg-secondary)] border-[var(--border)] text-[var(--text-secondary)] hover:text-white"
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        {/* Quick actions */}
        <div className="flex gap-2">
          <button
            onClick={onInterrupt}
            className="flex-1 px-3 py-2 rounded border border-[var(--warning)]/40 bg-[var(--warning)]/10 text-[var(--warning)] font-mono text-[11px] uppercase tracking-wider hover:bg-[var(--warning)]/20 transition-all"
          >
            Interrupt / Barge-in
          </button>
        </div>

        <div className="mt-4 text-[9px] text-[var(--text-muted)] leading-relaxed">
          Closing this panel (or the whole UI) does NOT stop Raphael. The runtime
          stays alive in the background (Section 1-4). Use SLEEP or EXIT to change that.
        </div>
      </div>
    </div>
  );
};
