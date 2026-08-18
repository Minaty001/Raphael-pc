import React from "react";
import { PageView, RaphaelStateType, SystemMetrics, RuntimeHealth, RuntimeHeartbeat, RuntimeModeType } from "../../types";
import { Cpu, MemoryStick, Disc, Mic, Radio, Terminal, Settings, Activity } from "lucide-react";

interface TopBarProps {
  status: "online" | "offline";
  state: RaphaelStateType;
  modelName: string;
  metrics: SystemMetrics | null;
  currentPage: PageView;
  onNavigate: (page: PageView) => void;
  onToggleDemoMode: () => void;
  isDemoMode: boolean;
  // Always-Alive additions (Sections 8, 37, 65, 67)
  alive?: boolean;
  health?: RuntimeHealth | null;
  heartbeat?: RuntimeHeartbeat | null;
  runtimeMode?: RuntimeModeType;
  taskCount?: number;
  onToggleRuntimePanel?: () => void;
  onToggleTaskDrawer?: () => void;
}

const STATE_COLORS: Record<string, string> = {
  idle: "text-[var(--accent-primary)] border-[var(--accent-primary)]/40 bg-[var(--accent-primary)]/10",
  listening: "text-[var(--success)] border-[var(--success)]/40 bg-[var(--success)]/10",
  thinking: "text-[var(--accent-secondary)] border-[var(--accent-secondary)]/40 bg-[var(--accent-secondary)]/10",
  executing: "text-[var(--warning)] border-[var(--warning)]/40 bg-[var(--warning)]/10",
  speaking: "text-[var(--accent-primary)] border-[var(--accent-primary)]/40 bg-[var(--accent-primary)]/10",
  error: "text-[var(--danger)] border-[var(--danger)]/40 bg-[var(--danger)]/10",
  offline: "text-[var(--text-muted)] border-[var(--text-muted)]/40 bg-white/5",
};

const MiniGauge: React.FC<{ icon: React.ReactNode; label: string; value: number; color: string }> = ({
  icon,
  label,
  value,
  color,
}) => (
  <div className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-[var(--bg-secondary)] border border-[var(--border)]">
    <span style={{ color }}>{icon}</span>
    <div className="flex flex-col leading-none">
      <span className="text-[9px] font-mono text-[var(--text-muted)] uppercase tracking-wider">{label}</span>
      <span className="text-[11px] font-mono font-semibold text-[var(--text-primary)]">{value.toFixed(0)}%</span>
    </div>
    <div className="w-12 h-1.5 rounded-full bg-white/10 overflow-hidden">
      <div className="h-full rounded-full transition-all duration-500" style={{ width: `${Math.min(100, value)}%`, background: color }} />
    </div>
  </div>
);

export const TopBar: React.FC<TopBarProps> = ({
  status,
  state,
  modelName,
  metrics,
  currentPage,
  onNavigate,
  onToggleDemoMode,
  isDemoMode,
  alive = false,
  health = null,
  heartbeat = null,
  runtimeMode = "NORMAL",
  taskCount = 0,
  onToggleRuntimePanel,
  onToggleTaskDrawer,
}) => {
  const cpu = metrics?.cpu_percent ?? 12;
  const ram = metrics?.memory_percent ?? 42;
  const disk = metrics?.disk_percent ?? 18;

  return (
    <header className="h-14 shrink-0 flex items-center justify-between px-4 border-b border-[var(--border)] bg-[#070c14]/90 backdrop-blur z-40 select-none">
      {/* Left: Brand + status */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => onNavigate("system")}
          className="flex items-center gap-2.5 hover:opacity-85 transition-opacity text-left group"
          title="View System Status"
        >
          <div className="w-8 h-8 rounded-md border border-[var(--accent-primary)]/50 bg-[var(--accent-primary)]/10 flex items-center justify-center text-[var(--accent-primary)] font-display font-bold text-sm shadow-[0_0_12px_var(--glow)] group-hover:shadow-[0_0_18px_var(--glow)] transition-shadow">
            R
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-display font-bold text-sm tracking-[0.2em] text-[var(--text-primary)]">RAPHAEL</h1>
              <span
                className={`w-2 h-2 rounded-full ${
                  status === "online" ? "bg-[var(--success)] shadow-[0_0_8px_var(--success)]" : "bg-[var(--danger)]"
                }`}
              />
            </div>
            <p className="text-[9px] font-mono text-[var(--text-muted)] tracking-[0.25em] uppercase">
              Cognitive Desktop AI · v3.0
            </p>
          </div>
        </button>

        {/* Current assistant state pill */}
        <div
          className={`hidden lg:flex items-center gap-1.5 px-3 py-1.5 rounded-full border font-mono text-[10px] uppercase tracking-widest font-bold ${
            STATE_COLORS[state] || STATE_COLORS.idle
          }`}
        >
          <Activity className="w-3 h-3" />
          {state}
        </div>

        {/* ALIVE indicator (Section 8/37) — click opens Runtime Panel */}
        <button
          onClick={onToggleRuntimePanel}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border font-mono text-[10px] uppercase tracking-widest font-bold transition-colors ${
            alive
              ? "text-[var(--success)] border-[var(--success)]/40 bg-[var(--success)]/10 hover:bg-[var(--success)]/20"
              : "text-[var(--text-muted)] border-[var(--text-muted)]/30 bg-white/5"
          }`}
          title="Raphael Runtime status — click for details"
        >
          <span
            className={`w-2 h-2 rounded-full ${
              alive ? "bg-[var(--success)] shadow-[0_0_8px_var(--success)] animate-pulse" : "bg-[var(--text-muted)]"
            }`}
          />
          {alive ? "ALIVE" : "OFFLINE"}
        </button>
      </div>

      {/* Center: Live telemetry */}
      <div className="hidden lg:flex items-center gap-2">
        <MiniGauge icon={<Cpu className="w-3.5 h-3.5" />} label="CPU" value={cpu} color="#56d9ff" />
        <MiniGauge icon={<MemoryStick className="w-3.5 h-3.5" />} label="RAM" value={ram} color="#4ce09a" />
        <MiniGauge icon={<Disc className="w-3.5 h-3.5" />} label="DISK" value={disk} color="#f4c95d" />
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[var(--bg-secondary)] border border-[var(--border)]">
          <Mic className="w-3.5 h-3.5 text-[var(--success)]" />
          <span className="text-[9px] font-mono text-[var(--text-muted)] uppercase tracking-wider">Voice</span>
          <span className="text-[11px] font-mono font-bold text-[var(--success)] uppercase">Ready</span>
        </div>
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[var(--bg-secondary)] border border-[var(--border)]">
          <span className="text-[9px] font-mono text-[var(--text-muted)] uppercase tracking-wider">Model</span>
          <span className="text-[11px] font-mono font-semibold text-[var(--accent-primary)]">{modelName}</span>
        </div>
      </div>

      {/* Right: Controls */}
      <div className="flex items-center gap-2">
        {/* Background task indicator (Section 38) */}
        <button
          onClick={onToggleTaskDrawer}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-mono transition-all ${
            taskCount > 0
              ? "bg-[var(--accent-secondary)]/15 border border-[var(--accent-secondary)]/40 text-[var(--accent-primary)]"
              : "bg-[var(--bg-secondary)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-white"
          }`}
          title="Background Tasks"
        >
          <span className="hidden sm:inline">⚙ {taskCount} Tasks</span>
        </button>

        <button
          onClick={onToggleDemoMode}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-mono transition-all ${
            isDemoMode
              ? "bg-[var(--warning)]/20 border border-[var(--warning)] text-[var(--warning)]"
              : "bg-[var(--bg-secondary)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-white"
          }`}
          title="Toggle Simulation Demo Mode"
        >
          <Radio className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">DEMO {isDemoMode ? "ON" : "OFF"}</span>
        </button>

        <button
          onClick={() => onNavigate("developer")}
          className={`p-2 rounded-md border transition-colors ${
            currentPage === "developer"
              ? "bg-[var(--accent-secondary)]/20 border-[var(--accent-secondary)] text-[var(--accent-primary)]"
              : "bg-[var(--bg-secondary)] border-[var(--border)] text-[var(--text-secondary)] hover:text-white"
          }`}
          title="Developer Telemetry Console"
        >
          <Terminal className="w-4 h-4" />
        </button>

        <button
          onClick={() => onNavigate("settings")}
          className={`p-2 rounded-md border transition-colors ${
            currentPage === "settings"
              ? "bg-[var(--accent-primary)]/20 border-[var(--accent-primary)] text-[var(--accent-primary)]"
              : "bg-[var(--bg-secondary)] border-[var(--border)] text-[var(--text-secondary)] hover:text-white"
          }`}
          title="Settings"
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
