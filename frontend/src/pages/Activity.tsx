import React from "react";
import { Activity, CheckCircle, Clock } from "lucide-react";

export const ActivityPage: React.FC = () => {
  const events = [
    { time: "13:42:10", type: "SCREEN", title: "Screen analyzed", desc: "Active app VS Code detected" },
    { time: "13:43:00", type: "MEMORY", title: "Memory retrieved", desc: "3 relevant preference facts retrieved" },
    { time: "13:44:15", type: "TOOL", title: "Tool executed", desc: "system_info status success (10.3ms)" },
    { time: "13:45:00", type: "LEARNING", title: "Self-Reflection Completed", desc: "Task executed cleanly" }
  ];

  return (
    <div className="h-full p-6 space-y-6 overflow-y-auto font-mono text-xs">
      <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
        <div className="flex items-center gap-2 text-sm font-bold text-[var(--accent-primary)] font-primary">
          <Activity className="w-5 h-5 text-[var(--accent-primary)]" />
          <span>CHRONOLOGICAL BRAIN ACTIVITY TIMELINE</span>
        </div>
        <span className="text-[10px] text-[var(--text-muted)]">REAL-TIME TIMELINE STREAM</span>
      </div>

      <div className="space-y-3 relative before:absolute before:left-3 before:top-2 before:bottom-2 before:w-0.5 before:bg-[var(--border)]">
        {events.map((evt, i) => (
          <div key={i} className="flex gap-4 items-start relative pl-8">
            <div className="absolute left-1.5 top-1.5 w-3 h-3 rounded-full bg-[var(--accent-primary)] border-2 border-[#05080d]" />
            <div className="glass-panel p-3 flex-1 space-y-1">
              <div className="flex justify-between items-center text-[10px] text-[var(--text-muted)]">
                <span className="text-[var(--accent-primary)] font-bold">{evt.type}</span>
                <span>{evt.time}</span>
              </div>
              <p className="text-xs text-white font-bold">{evt.title}</p>
              <p className="text-[11px] text-[var(--text-secondary)]">{evt.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
