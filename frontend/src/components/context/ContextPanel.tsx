import React from "react";
import { PageView } from "../../types";
import { Eye, Target, Sparkles, ChevronRight, Layers, ChevronLeft } from "lucide-react";

interface ContextPanelProps {
  context: {
    application?: string;
    window?: string;
    activity?: string;
    project?: string;
    activeGoal?: string;
    confidence?: number;
  };
  memoryCount?: number;
  onNavigate: (page: PageView) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export const ContextPanel: React.FC<ContextPanelProps> = ({
  context,
  memoryCount,
  onNavigate,
  collapsed,
  onToggleCollapse,
}) => {
  const confidence = Math.round((context.confidence ?? 0.94) * 100);

  if (collapsed) {
    return (
      <button
        onClick={onToggleCollapse}
        className="h-full w-9 shrink-0 flex flex-col items-center justify-center gap-2 border-l border-[var(--border)] bg-[#070c14]/90 hover:bg-[#0d151f] text-[var(--text-secondary)] hover:text-white transition-colors font-mono text-[10px]"
        title="Expand Context Panel"
      >
        <ChevronLeft className="w-4 h-4" />
        <span className="[writing-mode:vertical-rl] tracking-[0.2em] uppercase">Context</span>
      </button>
    );
  }

  return (
    <aside className="w-72 shrink-0 flex flex-col overflow-y-auto p-4 space-y-4 border-l border-[var(--border)] bg-[#070c14]/95 backdrop-blur font-mono text-xs z-30 select-none">
      <div className="flex items-center justify-between border-b border-[var(--border)] pb-2">
        <div className="flex items-center gap-1.5 font-display text-sm font-bold text-[var(--accent-primary)] uppercase tracking-wider">
          <Layers className="w-3.5 h-3.5" />
          <span>Context</span>
        </div>
        <button onClick={onToggleCollapse} className="btn-ghost p-1" title="Collapse Panel">
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Screen Awareness */}
      <div
        onClick={() => onNavigate("vision")}
        className="hud-card p-3 space-y-2 cursor-pointer hover:border-[var(--accent-primary)]/40 transition-colors group"
      >
        <div className="flex items-center justify-between text-[10px] text-[var(--accent-primary)] font-bold">
          <span className="flex items-center gap-1.5">
            <Eye className="w-3.5 h-3.5" /> SCREEN
          </span>
          {context.confidence != null && (
            <span className="text-[var(--success)]">{Math.round(context.confidence * 100)}%</span>
          )}
        </div>
        <div className="space-y-1 text-[11px]">
          <div>
            APP: <span className="text-white font-semibold">{context.application || "—"}</span>
          </div>
          <div className="truncate text-[var(--text-secondary)]">WIN: {context.window || "—"}</div>
          <div>
            ACT: <span className="text-[var(--accent-primary)]">{context.activity || "—"}</span>
          </div>
        </div>
      </div>

      {/* Active Goal */}
      <div className="hud-card p-3 space-y-2">
        <div className="flex items-center gap-1.5 text-[10px] text-[var(--accent-secondary)] font-bold">
          <Target className="w-3.5 h-3.5" /> ACTIVE GOAL
        </div>
        <p className="text-[12px] text-white font-semibold leading-snug">
          {context.activeGoal || "No active goal"}
        </p>
        {context.project && (
          <p className="text-[10px] text-[var(--text-secondary)]">Project: {context.project}</p>
        )}
      </div>

      {/* Relevant Memory */}
      <div className="hud-card p-3 space-y-2">
        <div className="flex items-center justify-between text-[10px] text-[var(--success)] font-bold">
          <span className="flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5" /> MEMORY
          </span>
          <span className="text-[var(--text-muted)] font-normal">
            {memoryCount != null ? `${memoryCount} stored` : ""}
          </span>
        </div>
        <button
          onClick={() => onNavigate("memory")}
          className="text-[10px] text-[var(--accent-primary)] hover:underline block w-full text-left"
        >
          View all memories →
        </button>
      </div>
    </aside>
  );
};
