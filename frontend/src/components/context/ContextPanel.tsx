import React from "react";
import { PageView } from "../../types";
import { Eye, Target, Sparkles, ChevronRight, AlertTriangle, Layers } from "lucide-react";

interface ContextPanelProps {
  context: {
    application?: string;
    window?: string;
    activity?: string;
    project?: string;
    activeGoal?: string;
    confidence?: number;
  };
  onNavigate: (page: PageView) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export const ContextPanel: React.FC<ContextPanelProps> = ({
  context,
  onNavigate,
  collapsed,
  onToggleCollapse
}) => {
  if (collapsed) {
    return (
      <button
        onClick={onToggleCollapse}
        className="h-full px-1.5 py-4 border-l border-[var(--border)] bg-[#070c14]/90 hover:bg-[#0d151f] text-[var(--text-secondary)] hover:text-white flex flex-col items-center justify-center transition-colors shrink-0 font-mono text-[10px]"
        title="Expand Context Panel"
      >
        <span className="[writing-mode:vertical-rl] tracking-widest uppercase">CURRENT CONTEXT</span>
      </button>
    );
  }

  return (
    <aside className="w-64 border-l border-[var(--border)] bg-[#070c14]/95 backdrop-blur flex flex-col shrink-0 overflow-y-auto p-4 space-y-4 font-mono text-xs z-30 select-none">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--border)] pb-2">
        <div className="flex items-center gap-1.5 font-bold text-[var(--accent-primary)]">
          <Layers className="w-3.5 h-3.5" />
          <span>CURRENT CONTEXT</span>
        </div>
        <button
          onClick={onToggleCollapse}
          className="p-1 hover:bg-[var(--bg-secondary)] rounded text-[var(--text-secondary)]"
          title="Collapse Panel"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Screen Awareness Card */}
      <div
        onClick={() => onNavigate("vision")}
        className="glass-panel p-3 space-y-2 cursor-pointer hover:border-[var(--accent-primary)]/40 transition-all group"
      >
        <div className="flex items-center justify-between text-[10px] text-[var(--accent-primary)] font-bold">
          <span className="flex items-center gap-1"><Eye className="w-3.5 h-3.5" /> SCREEN AWARENESS</span>
          <span className="text-[var(--success)]">{Math.round((context.confidence || 0.94) * 100)}%</span>
        </div>

        <div className="space-y-1 text-[11px]">
          <div>APP: <span className="text-white font-semibold">{context.application || "VS Code"}</span></div>
          <div className="truncate text-[var(--text-secondary)]">WIN: {context.window || "Raphael Project Workspace"}</div>
          <div>ACT: <span className="text-[var(--accent-primary)]">{context.activity || "Python Development"}</span></div>
        </div>

        <div className="flex items-center gap-1 text-[10px] text-[var(--warning)] pt-1 border-t border-[var(--border)]">
          <AlertTriangle className="w-3 h-3" />
          <span>Last analyzed: 2.1s ago</span>
        </div>
      </div>

      {/* Active Project & Goal */}
      <div className="glass-panel p-3 space-y-2">
        <div className="flex items-center gap-1.5 text-[10px] text-[var(--accent-secondary)] font-bold">
          <Target className="w-3.5 h-3.5" />
          <span>ACTIVE GOAL</span>
        </div>
        <p className="text-[11px] text-white font-semibold">{context.activeGoal || "Cognitive Memory & Vision System"}</p>
        <p className="text-[10px] text-[var(--text-secondary)]">Project: {context.project || "Raphael v3"}</p>
      </div>

      {/* Relevant Contextual Memory */}
      <div className="glass-panel p-3 space-y-2">
        <div className="flex items-center gap-1.5 text-[10px] text-[var(--success)] font-bold">
          <Sparkles className="w-3.5 h-3.5" />
          <span>RELEVANT MEMORY</span>
        </div>
        <ul className="text-[11px] text-[var(--text-secondary)] space-y-1">
          <li>• User prefers local models.</li>
          <li>• Wake word: "Raphael"</li>
          <li>• Resource mode: BALANCED</li>
        </ul>
        <button
          onClick={() => onNavigate("memory")}
          className="text-[10px] text-[var(--accent-primary)] hover:underline block pt-1"
        >
          View all 12,842 memories →
        </button>
      </div>
    </aside>
  );
};
