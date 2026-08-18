import React from "react";
import { Repeat, CheckCircle, ShieldAlert } from "lucide-react";

export const Routines: React.FC = () => {
  const routines = [
    {
      name: "Morning Workspace Initialization",
      sequence: ["07:45 Chrome", "07:55 VS Code", "08:02 Raphael Backend"],
      confidence: 0.87,
      observedCount: 18,
      status: "Candidate Pattern"
    }
  ];

  return (
    <div className="h-full p-6 space-y-6 overflow-y-auto font-mono text-xs">
      <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
        <div className="flex items-center gap-2 text-sm font-bold text-[var(--accent-primary)] font-primary">
          <Repeat className="w-5 h-5 text-[var(--accent-primary)]" />
          <span>LEARNED DAILY ROUTINES & WORKFLOWS</span>
        </div>
        <span className="text-[10px] text-[var(--text-muted)]">REQUIRES USER PERMISSION TO AUTOMATE</span>
      </div>

      <div className="space-y-4">
        {routines.map((rt, i) => (
          <div key={i} className="glass-panel p-4 space-y-3">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="text-sm font-bold text-white font-primary">{rt.name}</h3>
                <span className="text-[10px] text-[var(--warning)] font-semibold">Observed {rt.observedCount} times</span>
              </div>
              <span className="text-[var(--success)] font-bold">Confidence: {Math.round(rt.confidence * 100)}%</span>
            </div>

            <div className="p-3 bg-[var(--bg-secondary)] rounded border border-[var(--border)] space-y-1">
              <span className="text-[10px] text-[var(--text-muted)]">OBSERVED SEQUENCE:</span>
              <div className="flex flex-wrap gap-2 text-xs text-[var(--text-primary)]">
                {rt.sequence.map((step, idx) => (
                  <span key={idx} className="px-2 py-0.5 rounded bg-[var(--accent-primary)]/10 border border-[var(--accent-primary)]/30 text-[var(--accent-primary)]">
                    {step}
                  </span>
                ))}
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <button className="px-3 py-1.5 bg-[var(--success)]/20 border border-[var(--success)]/40 text-[var(--success)] rounded font-bold hover:bg-[var(--success)]/30">
                ENABLE AUTOMATION
              </button>
              <button className="px-3 py-1.5 bg-[var(--bg-secondary)] border border-[var(--border)] text-[var(--text-secondary)] rounded hover:text-white">
                IGNORE
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
