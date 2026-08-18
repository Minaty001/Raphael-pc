import React from "react";
import { Bell, Clock, Eye } from "lucide-react";

export const Reminders: React.FC = () => {
  const reminders = [
    { type: "CONTEXTUAL", trigger: "When VS Code opens", text: "Run Raphael unit & integration test suite.", status: "Pending" },
    { type: "TIME_BASED", trigger: "Today at 18:00", text: "Review daily cognitive memory summary.", status: "Pending" }
  ];

  return (
    <div className="h-full p-6 space-y-6 overflow-y-auto font-mono text-xs">
      <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
        <div className="flex items-center gap-2 text-sm font-bold text-[var(--accent-primary)] font-primary">
          <Bell className="w-5 h-5 text-[var(--accent-primary)]" />
          <span>CONTEXTUAL & SCHEDULED REMINDERS</span>
        </div>
        <span className="text-[10px] text-[var(--text-muted)]">2 PENDING REMINDERS</span>
      </div>

      <div className="space-y-4">
        {reminders.map((rem, i) => (
          <div key={i} className="glass-panel p-4 space-y-2">
            <div className="flex justify-between items-center text-[10px]">
              <span className="px-2 py-0.5 rounded bg-[var(--accent-primary)]/15 border border-[var(--accent-primary)]/40 text-[var(--accent-primary)] font-bold">
                {rem.type}: {rem.trigger}
              </span>
              <span className="text-[var(--warning)] font-bold">{rem.status}</span>
            </div>
            <p className="text-xs text-white font-primary font-semibold">{rem.text}</p>
          </div>
        ))}
      </div>
    </div>
  );
};
