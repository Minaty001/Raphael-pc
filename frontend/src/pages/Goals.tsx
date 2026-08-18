import React from "react";
import { Target, CheckCircle, Clock } from "lucide-react";

export const Goals: React.FC = () => {
  const activeGoals = [
    { title: "Raphael v3 Cognitive Brain", progress: 85, priority: "HIGH", project: "Raphael PC" },
    { title: "Sherpa-ONNX Voice Pipeline", progress: 60, priority: "MEDIUM", project: "Voice Engine" },
    { title: "Multimodal Screen Perception", progress: 40, priority: "HIGH", project: "Vision" }
  ];

  return (
    <div className="h-full p-6 space-y-6 overflow-y-auto font-mono text-xs">
      <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
        <div className="flex items-center gap-2 text-sm font-bold text-[var(--accent-primary)] font-primary">
          <Target className="w-5 h-5 text-[var(--accent-primary)]" />
          <span>ACTIVE GOALS & LONG-TERM OBJECTIVES</span>
        </div>
        <span className="text-[10px] text-[var(--text-muted)]">3 ACTIVE OBJECTIVES</span>
      </div>

      <div className="space-y-4">
        {activeGoals.map((goal, i) => (
          <div key={i} className="glass-panel p-4 space-y-3">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="text-sm font-bold text-white font-primary">{goal.title}</h3>
                <span className="text-[10px] text-[var(--text-muted)]">Project: {goal.project}</span>
              </div>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                goal.priority === "HIGH" ? "bg-[var(--danger)]/20 text-[var(--danger)] border border-[var(--danger)]/40" : "bg-[var(--warning)]/20 text-[var(--warning)] border border-[var(--warning)]/40"
              }`}>
                {goal.priority} PRIORITY
              </span>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-[10px]">
                <span className="text-[var(--text-secondary)]">Progress</span>
                <span className="text-[var(--accent-primary)] font-bold">{goal.progress}%</span>
              </div>
              <div className="h-2 bg-[var(--bg-secondary)] rounded-full overflow-hidden border border-[var(--border)]">
                <div
                  className="h-full bg-[var(--accent-primary)] transition-all duration-500"
                  style={{ width: `${goal.progress}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
