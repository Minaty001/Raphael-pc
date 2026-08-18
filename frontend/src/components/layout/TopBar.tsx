import React from "react";
import { PageView, RaphaelStateType, SystemMetrics } from "../../types";
import { Cpu, Server, Mic, Bell, Terminal, Settings, Radio } from "lucide-react";

interface TopBarProps {
  status: "online" | "offline";
  state: RaphaelStateType;
  modelName: string;
  metrics: SystemMetrics | null;
  currentPage: PageView;
  onNavigate: (page: PageView) => void;
  onToggleDemoMode: () => void;
  isDemoMode: boolean;
}

export const TopBar: React.FC<TopBarProps> = ({
  status,
  state,
  modelName,
  metrics,
  currentPage,
  onNavigate,
  onToggleDemoMode,
  isDemoMode
}) => {
  const cpu = metrics?.cpu_percent ?? 12;
  const ram = metrics?.memory_percent ?? 42;

  return (
    <header className="px-5 py-2.5 border-b border-[var(--border)] bg-[#070c14]/90 backdrop-blur shrink-0 flex items-center justify-between z-40 select-none">
      {/* Left: Raphael Logo & Status */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => onNavigate("system")}
          className="flex items-center gap-2.5 hover:opacity-85 transition-opacity text-left group"
          title="Click to view System Status"
        >
          <div className="w-7 h-7 rounded border border-[var(--accent-primary)]/50 bg-[var(--accent-primary)]/10 flex items-center justify-center text-[var(--accent-primary)] font-bold text-xs shadow-[0_0_10px_var(--glow)]">
            R
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-bold text-xs tracking-wider text-[var(--text-primary)]">RAPHAEL</h1>
              <span className={`w-2 h-2 rounded-full ${status === "online" ? "bg-[var(--success)] shadow-[0_0_8px_var(--success)]" : "bg-[var(--danger)]"}`} />
              <span className="text-[10px] font-mono text-[var(--text-secondary)] uppercase">{status}</span>
            </div>
            <p className="text-[9px] font-mono text-[var(--text-muted)] tracking-widest uppercase">COGNITIVE DESKTOP AI v3.0</p>
          </div>
        </button>
      </div>

      {/* Middle: Live System Telemetry Bar */}
      <div className="hidden md:flex items-center gap-5 text-xs font-mono">
        {/* Model */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[var(--bg-secondary)] border border-[var(--border)]">
          <span className="text-[var(--text-muted)]">Model:</span>
          <span className="text-[var(--accent-primary)] font-semibold">{modelName}</span>
        </div>

        {/* CPU */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[var(--bg-secondary)] border border-[var(--border)]">
          <Cpu className="w-3 h-3 text-[var(--accent-primary)]" />
          <span className="text-[var(--text-muted)]">CPU:</span>
          <span className="text-[var(--text-primary)] font-semibold">{cpu.toFixed(0)}%</span>
        </div>

        {/* RAM */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[var(--bg-secondary)] border border-[var(--border)]">
          <Server className="w-3 h-3 text-[var(--success)]" />
          <span className="text-[var(--text-muted)]">RAM:</span>
          <span className="text-[var(--text-primary)] font-semibold">{ram.toFixed(0)}%</span>
        </div>

        {/* Voice status */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[var(--bg-secondary)] border border-[var(--border)]">
          <Mic className="w-3 h-3 text-[var(--success)]" />
          <span className="text-[var(--text-muted)]">Voice:</span>
          <span className="text-[var(--success)] font-bold uppercase">READY</span>
        </div>
      </div>

      {/* Right Controls: Notifications, Demo Mode, Developer Mode, Settings */}
      <div className="flex items-center gap-2">
        <button
          onClick={onToggleDemoMode}
          className={`flex items-center gap-1 px-2.5 py-1.5 rounded text-xs font-mono transition-all ${
            isDemoMode
              ? "bg-[var(--warning)]/20 border border-[var(--warning)] text-[var(--warning)]"
              : "bg-[var(--bg-secondary)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-white"
          }`}
          title="Toggle Simulation Demo Mode"
        >
          <Radio className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">DEMO: {isDemoMode ? "ON" : "OFF"}</span>
        </button>

        <button
          onClick={() => onNavigate("developer")}
          className={`p-1.5 rounded border transition-colors ${
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
          className={`p-1.5 rounded border transition-colors ${
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
