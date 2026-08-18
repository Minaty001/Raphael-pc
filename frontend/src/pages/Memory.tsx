import React, { useState } from "react";
import { Brain, Search, Trash2, Edit3, ShieldCheck, Sparkles, Filter } from "lucide-react";

interface MemoryProps {
  onForgetMemory: (keyword: string) => void;
}

export const Memory: React.FC<MemoryProps> = ({ onForgetMemory }) => {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");

  const memoryStats = [
    { label: "Total Memories", value: "12,842", icon: <Brain className="w-4 h-4 text-[var(--accent-primary)]" /> },
    { label: "Episodes", value: "1,204", icon: <Sparkles className="w-4 h-4 text-[var(--accent-secondary)]" /> },
    { label: "Preferences", value: "184", icon: <ShieldCheck className="w-4 h-4 text-[var(--success)]" /> },
    { label: "Skills", value: "43", icon: <Filter className="w-4 h-4 text-[var(--warning)]" /> }
  ];

  const sampleMemories = [
    { id: 1, type: "PREFERENCE", content: "User prefers local LLM models when offline.", confidence: 0.94, evidence: 14 },
    { id: 2, type: "FACT", content: "Active desktop OS is Linux Mint / Ubuntu.", confidence: 0.99, evidence: 42 },
    { id: 3, type: "SKILL", content: "start_raphael workflow procedure v1", confidence: 0.90, evidence: 8 },
    { id: 4, type: "RULE", content: "High-risk tool execution requires explicit user confirmation.", confidence: 1.0, evidence: 100 }
  ];

  const handleForgetClick = (content: str) => {
    onForgetMemory(content);
  };

  return (
    <div className="h-full p-6 space-y-6 overflow-y-auto font-mono text-xs">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
        <div className="flex items-center gap-2 text-sm font-bold text-[var(--accent-primary)] font-primary">
          <Brain className="w-5 h-5 text-[var(--accent-primary)]" />
          <span>RAPHAEL 5-TIER MEMORY DASHBOARD</span>
        </div>
        <span className="text-[10px] text-[var(--text-muted)]">HYBRID VECTOR & SQLITE STORE</span>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {memoryStats.map((stat, i) => (
          <div key={i} className="glass-panel p-4 space-y-1">
            <div className="flex items-center justify-between text-[var(--text-muted)]">
              <span>{stat.label}</span>
              {stat.icon}
            </div>
            <div className="text-xl font-bold text-white font-primary">{stat.value}</div>
          </div>
        ))}
      </div>

      {/* Search Bar & Filters */}
      <div className="glass-panel p-3 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search memory graph..."
            className="w-full bg-[var(--bg-secondary)] border border-[var(--border)] rounded pl-8 pr-3 py-1.5 text-xs text-white placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-primary)]"
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto">
          {["All", "Facts", "Preferences", "Episodes", "Skills"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2.5 py-1 rounded text-[11px] transition-all ${
                filter === f
                  ? "bg-[var(--accent-primary)]/20 border border-[var(--accent-primary)] text-[var(--accent-primary)] font-bold"
                  : "bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:text-white"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Memory Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sampleMemories.map((mem) => (
          <div key={mem.id} className="glass-panel p-4 space-y-3 flex flex-col justify-between">
            <div className="space-y-1.5">
              <div className="flex justify-between items-center text-[10px]">
                <span className="px-2 py-0.5 rounded bg-[var(--accent-primary)]/15 border border-[var(--accent-primary)]/40 text-[var(--accent-primary)] font-bold">
                  {mem.type}
                </span>
                <span className="text-[var(--success)] font-bold">Confidence: {Math.round(mem.confidence * 100)}%</span>
              </div>
              <p className="text-xs text-[var(--text-primary)] font-primary">{mem.content}</p>
            </div>

            <div className="flex justify-between items-center pt-2 border-t border-[var(--border)] text-[10px] text-[var(--text-muted)]">
              <span>Learned from {mem.evidence} interactions</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleForgetClick(mem.content)}
                  className="px-2 py-1 bg-[var(--danger)]/15 border border-[var(--danger)]/40 text-[var(--danger)] rounded hover:bg-[var(--danger)]/30 flex items-center gap-1"
                >
                  <Trash2 className="w-3 h-3" />
                  <span>FORGET</span>
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
