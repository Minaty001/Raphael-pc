import React, { useState } from "react";
import { Brain, Target, Repeat, Eye, Trash2, Sparkles } from "lucide-react";

interface Props {
  contextSummary: any;
  userProfile: any;
  goals: any[];
  openLoops: any[];
  onForgetMemory: (keyword: string) => void;
}

export const CognitiveBrainPanel: React.FC<Props> = ({
  contextSummary,
  userProfile,
  goals,
  openLoops,
  onForgetMemory
}) => {
  const [forgetKw, setForgetKw] = useState("");

  const handleForgetSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!forgetKw.trim()) return;
    onForgetMemory(forgetKw.trim());
    setForgetKw("");
  };

  const screenState = contextSummary?.recent_screen || {};

  return (
    <div className="hud-card p-4 space-y-4 max-h-[550px] overflow-y-auto font-mono text-xs">
      <div className="hud-header py-1 px-0 justify-between border-b border-emerald-500/20 text-xs">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-emerald-400" />
          <span>COGNITIVE BRAIN & MEMORY ENGINE</span>
        </div>
        <span className="text-[10px] text-emerald-400/80">L0-L5 ACTIVE</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
        {/* Active Goal */}
        <div className="bg-slate-950/60 p-3 rounded border border-slate-800 space-y-1.5">
          <div className="flex items-center gap-1.5 text-cyan-400 font-bold">
            <Target className="w-3.5 h-3.5" />
            <span>ACTIVE GOAL:</span>
          </div>
          <p className="text-slate-200">{contextSummary?.active_goal || "Build Raphael PC v3 Cognitive Assistant"}</p>
        </div>

        {/* Screen Understanding Perception */}
        <div className="bg-slate-950/60 p-3 rounded border border-slate-800 space-y-1.5">
          <div className="flex items-center gap-1.5 text-emerald-400 font-bold">
            <Eye className="w-3.5 h-3.5" />
            <span>SCREEN PERCEPTION:</span>
          </div>
          <div className="text-[11px] text-slate-300 space-y-0.5 truncate">
            <div>APP: <span className="text-emerald-300 font-semibold">{screenState.active_app || "VS Code / Browser"}</span></div>
            <div className="truncate">WINDOW: <span className="text-slate-400">{screenState.window_title || "Raphael Development Workspace"}</span></div>
            <div>ACTIVITY: <span className="text-cyan-300">{screenState.activity || "Coding / Development"}</span></div>
          </div>
        </div>

        {/* Open Discussion Loops */}
        <div className="bg-slate-950/60 p-3 rounded border border-slate-800 space-y-1.5 md:col-span-2">
          <div className="flex items-center justify-between text-amber-400 font-bold">
            <div className="flex items-center gap-1.5">
              <Repeat className="w-3.5 h-3.5" />
              <span>OPEN LOOPS ({openLoops.length}):</span>
            </div>
          </div>
          {openLoops.length === 0 ? (
            <p className="text-slate-500 text-[11px]">No unresolved discussion loops.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {openLoops.map((loop, i) => (
                <span key={i} className="px-2 py-0.5 rounded bg-amber-950/60 border border-amber-500/30 text-amber-300 text-[11px]">
                  • {loop.topic}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* User Model Preferences Profile */}
        <div className="bg-slate-950/60 p-3 rounded border border-slate-800 space-y-2 md:col-span-2">
          <div className="flex items-center gap-1.5 text-purple-400 font-bold">
            <Sparkles className="w-3.5 h-3.5" />
            <span>LEARNED USER MODEL PREFERENCES:</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
            {Object.keys(userProfile).length === 0 ? (
              <span className="text-slate-500 col-span-2">No explicit user preferences stored yet.</span>
            ) : (
              Object.entries(userProfile).map(([key, val]: [string, any], i) => (
                <div key={i} className="p-2 bg-slate-900/80 rounded border border-slate-800 flex justify-between items-center">
                  <span className="text-slate-400">{key}:</span>
                  <span className="text-purple-300 font-semibold">{String(val.value)}</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Forget Memory Input Form */}
        <div className="bg-slate-950/60 p-3 rounded border border-slate-800 space-y-2 md:col-span-2">
          <form onSubmit={handleForgetSubmit} className="flex items-center gap-2">
            <Trash2 className="w-4 h-4 text-rose-400 shrink-0" />
            <input
              type="text"
              value={forgetKw}
              onChange={(e) => setForgetKw(e.target.value)}
              placeholder="Enter keyword to purge memory (e.g. 'Ollama preference')..."
              className="flex-1 bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-rose-500/50"
            />
            <button
              type="submit"
              disabled={!forgetKw.trim()}
              className="px-3 py-1.5 bg-rose-950/60 border border-rose-500/40 text-rose-300 rounded text-xs hover:bg-rose-900/60 disabled:opacity-40"
            >
              FORGET
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
