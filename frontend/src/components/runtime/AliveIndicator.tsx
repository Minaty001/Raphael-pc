import React from "react";
import { RuntimeHeartbeat, RuntimeModeType } from "../../types";

/**
 * AliveIndicator — compact "Raphael is alive" status (Section 67).
 * `alive` means: runtime process exists, event loop running, scheduler active,
 * wake-word healthy, websocket available, workers healthy (Section 8).
 */
export const AliveIndicator: React.FC<{
  status: "alive" | "offline";
  uptime: number;
  workers: number;
  tasks?: number;
}> = ({ status, uptime, workers, tasks }) => {
  const alive = status === "alive";
  const fmt = (s: number) => {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return `${h}h ${m}m`;
  };

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2">
        <span
          className={`w-2.5 h-2.5 rounded-full ${alive ? "bg-[var(--success)] shadow-[0_0_8px_var(--success)] animate-pulse" : "bg-[var(--text-muted)]"}`}
        />
        <span
          className={`font-display text-xs tracking-widest uppercase ${
            alive ? "text-[var(--success)]" : "text-[var(--text-muted)]"
          }`}
        >
          {alive ? "RAPHAEL ALIVE" : "OFFLINE"}
        </span>
      </div>
      <div className="flex flex-col leading-none font-mono text-[10px] text-[var(--text-secondary)]">
        <span>Uptime {fmt(uptime)}</span>
        <span>
          {workers} workers{typeof tasks === "number" ? ` · ${tasks} tasks` : ""}
        </span>
      </div>
    </div>
  );
};
