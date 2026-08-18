import React from "react";
import { Server, Cpu, HardDrive, Activity } from "lucide-react";
import { SystemMetrics } from "../types";

interface SystemProps {
  metrics: SystemMetrics | null;
}

export const System: React.FC<SystemProps> = ({ metrics }) => {
  const cpu = metrics?.cpu_percent ?? 12;
  const ram = metrics?.memory_percent ?? 42;
  const disk = metrics?.disk_percent ?? 18;

  return (
    <div className="h-full p-6 space-y-6 overflow-y-auto font-mono text-xs">
      <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
        <div className="flex items-center gap-2 text-sm font-bold text-[var(--accent-primary)] font-primary">
          <Server className="w-5 h-5 text-[var(--accent-primary)]" />
          <span>SYSTEM HARDWARE TELEMETRY & METRICS</span>
        </div>
        <span className="text-[10px] text-[var(--success)] font-bold">MODE: BALANCED</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* CPU */}
        <div className="glass-panel p-4 space-y-2">
          <div className="flex justify-between items-center text-[var(--text-muted)]">
            <span className="flex items-center gap-1.5 font-bold"><Cpu className="w-4 h-4 text-[var(--accent-primary)]" /> CPU UTILIZATION</span>
            <span className="text-[var(--accent-primary)] font-bold text-sm">{cpu.toFixed(1)}%</span>
          </div>
          <div className="h-2 bg-[var(--bg-secondary)] rounded-full overflow-hidden border border-[var(--border)]">
            <div className="h-full bg-[var(--accent-primary)] transition-all duration-300" style={{ width: `${cpu}%` }} />
          </div>
        </div>

        {/* RAM */}
        <div className="glass-panel p-4 space-y-2">
          <div className="flex justify-between items-center text-[var(--text-muted)]">
            <span className="flex items-center gap-1.5 font-bold"><Server className="w-4 h-4 text-[var(--success)]" /> RAM MEMORY</span>
            <span className="text-[var(--success)] font-bold text-sm">{ram.toFixed(1)}%</span>
          </div>
          <div className="h-2 bg-[var(--bg-secondary)] rounded-full overflow-hidden border border-[var(--border)]">
            <div className="h-full bg-[var(--success)] transition-all duration-300" style={{ width: `${ram}%` }} />
          </div>
        </div>

        {/* DISK */}
        <div className="glass-panel p-4 space-y-2">
          <div className="flex justify-between items-center text-[var(--text-muted)]">
            <span className="flex items-center gap-1.5 font-bold"><HardDrive className="w-4 h-4 text-[var(--warning)]" /> DISK USAGE</span>
            <span className="text-[var(--warning)] font-bold text-sm">{disk.toFixed(1)}%</span>
          </div>
          <div className="h-2 bg-[var(--bg-secondary)] rounded-full overflow-hidden border border-[var(--border)]">
            <div className="h-full bg-[var(--warning)] transition-all duration-300" style={{ width: `${disk}%` }} />
          </div>
        </div>
      </div>
    </div>
  );
};
