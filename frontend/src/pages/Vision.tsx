import React, { useState } from "react";
import { Eye, Shield, AlertCircle, RefreshCw } from "lucide-react";

export const Vision: React.FC = () => {
  const [privacyMode, setPrivacyMode] = useState<"OFF" | "ON_DEMAND" | "SMART" | "CONTINUOUS">("ON_DEMAND");

  return (
    <div className="h-full p-6 space-y-6 overflow-y-auto font-mono text-xs">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
        <div className="flex items-center gap-2 text-sm font-bold text-[var(--accent-primary)] font-primary">
          <Eye className="w-5 h-5 text-[var(--accent-primary)]" />
          <span>DESKTOP VISION & SCREEN PERCEPTION</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[var(--text-muted)]">PRIVACY MODE:</span>
          {["OFF", "ON_DEMAND", "SMART", "CONTINUOUS"].map((m) => (
            <button
              key={m}
              onClick={() => setPrivacyMode(m as any)}
              className={`px-2.5 py-1 rounded text-[10px] transition-all ${
                privacyMode === m
                  ? "bg-[var(--accent-primary)]/20 border border-[var(--accent-primary)] text-[var(--accent-primary)] font-bold"
                  : "bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:text-white"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* Main Screen Preview & Detection Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Screen Preview Container */}
        <div className="lg:col-span-7 glass-panel p-4 space-y-3">
          <div className="flex justify-between items-center text-[11px] text-[var(--accent-primary)] font-bold">
            <span>LIVE SCREEN STREAM PREVIEW</span>
            <span className="text-[var(--success)]">Analyzed 2.1s ago</span>
          </div>

          <div className="w-full h-[240px] bg-[#020408] rounded border border-[var(--border)] flex flex-col items-center justify-center text-center p-4 relative overflow-hidden">
            <div className="absolute inset-0 bg-cyan-500/5 backdrop-blur-[1px] flex flex-col items-center justify-center">
              <Eye className="w-10 h-10 text-[var(--accent-primary)]/60 mb-2" />
              <p className="text-white font-primary font-bold text-sm">VS Code — Raphael v3 Development Workspace</p>
              <p className="text-[10px] text-[var(--text-secondary)]">Active File: <code>raphael/brain/cognitive_runtime.py</code></p>
            </div>
          </div>
        </div>

        {/* Detected UI Elements & Semantic Interpretation */}
        <div className="lg:col-span-5 glass-panel p-4 space-y-4">
          <div className="flex items-center gap-2 text-xs font-bold text-[var(--accent-secondary)]">
            <Shield className="w-4 h-4" />
            <span>SEMANTIC SCREEN ANALYSIS</span>
          </div>

          <div className="space-y-2 text-xs">
            <div className="p-2.5 bg-[var(--bg-secondary)] rounded border border-[var(--border)]">
              <span className="text-[var(--text-muted)] text-[10px]">APPLICATION:</span>
              <p className="text-white font-semibold">VS Code (Visual Studio Code)</p>
            </div>

            <div className="p-2.5 bg-[var(--bg-secondary)] rounded border border-[var(--border)]">
              <span className="text-[var(--text-muted)] text-[10px]">DETECTED ACTIVITY:</span>
              <p className="text-[var(--accent-primary)] font-semibold">Python Backend Development & Testing</p>
            </div>

            <div className="p-2.5 bg-[var(--bg-secondary)] rounded border border-[var(--border)] space-y-1">
              <span className="text-[var(--text-muted)] text-[10px]">DETECTED UI ELEMENTS:</span>
              <ul className="text-[11px] text-[var(--text-secondary)] space-y-0.5">
                <li>• Editor Terminal (15 test cases passed)</li>
                <li>• Explorer Panel (`raphael/memory/vector_store.py`)</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
