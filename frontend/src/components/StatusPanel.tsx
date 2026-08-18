import React from "react";
import { SystemMetrics } from "../types";
import { Cpu, HardDrive, Server, Shield, Activity } from "lucide-react";

interface Props {
  metrics: SystemMetrics | null;
  isConnected: boolean;
  resourceMode: string;
  activeModel: string;
}

export const StatusPanel: React.FC<Props> = ({
  metrics,
  isConnected,
  resourceMode,
  activeModel
}) => {
  const cpu = metrics?.cpu_percent ?? 0;
  const ram = metrics?.memory_percent ?? 0;
  const disk = metrics?.disk_percent ?? 0;

  return (
    <div className="hud-card p-3 space-y-3 font-mono text-xs">
      <div className="hud-header py-1 px-0 justify-between border-b border-cyan-500/20 text-xs">
        <div className="flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          <span>SYSTEM TELEMETRY</span>
        </div>
        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
          isConnected ? "bg-emerald-950/80 text-emerald-400 border border-emerald-500/30" : "bg-rose-950/80 text-rose-400 border border-rose-500/30"
        }`}>
          {isConnected ? "ONLINE" : "OFFLINE"}
        </span>
      </div>

      {/* Mini 3-Column Resource Meters */}
      <div className="grid grid-cols-3 gap-2">
        {/* CPU Meter */}
        <div className="bg-slate-950/60 p-2 rounded border border-slate-800 space-y-1">
          <div className="flex justify-between text-[10px] text-slate-400">
            <span className="flex items-center gap-1"><Cpu className="w-3 h-3 text-cyan-400" /> CPU</span>
            <span className="text-cyan-300 font-bold">{cpu.toFixed(0)}%</span>
          </div>
          <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-cyan-400 transition-all duration-300"
              style={{ width: `${Math.min(100, Math.max(0, cpu))}%` }}
            />
          </div>
        </div>

        {/* RAM Meter */}
        <div className="bg-slate-950/60 p-2 rounded border border-slate-800 space-y-1">
          <div className="flex justify-between text-[10px] text-slate-400">
            <span className="flex items-center gap-1"><Server className="w-3 h-3 text-emerald-400" /> RAM</span>
            <span className="text-emerald-300 font-bold">{ram.toFixed(0)}%</span>
          </div>
          <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-emerald-400 transition-all duration-300"
              style={{ width: `${Math.min(100, Math.max(0, ram))}%` }}
            />
          </div>
        </div>

        {/* Disk Meter */}
        <div className="bg-slate-950/60 p-2 rounded border border-slate-800 space-y-1">
          <div className="flex justify-between text-[10px] text-slate-400">
            <span className="flex items-center gap-1"><HardDrive className="w-3 h-3 text-amber-400" /> DISK</span>
            <span className="text-amber-300 font-bold">{disk.toFixed(0)}%</span>
          </div>
          <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-amber-400 transition-all duration-300"
              style={{ width: `${Math.min(100, Math.max(0, disk))}%` }}
            />
          </div>
        </div>
      </div>

      {/* Mode & Active Model Bar */}
      <div className="flex justify-between items-center text-[10px] text-slate-400 pt-1 border-t border-slate-800/80">
        <div className="flex items-center gap-1">
          <Shield className="w-3 h-3 text-purple-400" />
          <span>MODE: <strong className="text-purple-300">{resourceMode}</strong></span>
        </div>
        <div>
          <span>MODEL: <strong className="text-cyan-300 uppercase">{activeModel}</strong></span>
        </div>
      </div>
    </div>
  );
};
