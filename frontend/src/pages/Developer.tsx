import React, { useState } from "react";
import { Terminal, Activity, Database, Wrench } from "lucide-react";
import { WSEvent } from "../types";

interface DeveloperProps {
  events: WSEvent[];
  tools: any[];
  memories: any[];
}

export const Developer: React.FC<DeveloperProps> = ({ events, tools, memories }) => {
  const [tab, setTab] = useState<"events" | "tools" | "memories">("events");

  const perfMetrics = [
    { label: "Startup Time", value: "1.8s" },
    { label: "Idle RAM", value: "420 MB" },
    { label: "STT Latency", value: "380 ms" },
    { label: "LLM TTFB", value: "620 ms" },
    { label: "WebSocket Latency", value: "14 ms" },
    { label: "Vision Processing", value: "820 ms" }
  ];

  return (
    <div className="h-full p-6 space-y-6 overflow-y-auto font-mono text-xs">
      <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
        <div className="flex items-center gap-2 text-sm font-bold text-[var(--accent-primary)] font-primary">
          <Terminal className="w-5 h-5 text-[var(--accent-primary)]" />
          <span>DEVELOPER TELEMETRY & BRAIN INSPECTOR</span>
        </div>
        <span className="text-[10px] text-[var(--success)] font-bold">WEBSOCKET CONNECTED</span>
      </div>

      {/* Performance Panel */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
        {perfMetrics.map((p, i) => (
          <div key={i} className="glass-panel p-2.5 space-y-0.5">
            <span className="text-[10px] text-[var(--text-muted)] block">{p.label}</span>
            <span className="text-xs font-bold text-[var(--accent-primary)] font-primary">{p.value}</span>
          </div>
        ))}
      </div>

      {/* Tab Controls */}
      <div className="flex items-center gap-2 border-b border-[var(--border)] pb-2">
        <button
          onClick={() => setTab("events")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded transition-all ${
            tab === "events" ? "bg-[var(--accent-primary)]/20 text-[var(--accent-primary)] border border-[var(--accent-primary)]/50 font-bold" : "text-[var(--text-secondary)] hover:text-white"
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          <span>LIVE EVENT STREAM ({events.length})</span>
        </button>

        <button
          onClick={() => setTab("tools")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded transition-all ${
            tab === "tools" ? "bg-[var(--accent-primary)]/20 text-[var(--accent-primary)] border border-[var(--accent-primary)]/50 font-bold" : "text-[var(--text-secondary)] hover:text-white"
          }`}
        >
          <Wrench className="w-3.5 h-3.5" />
          <span>REGISTERED TOOLS ({tools.length})</span>
        </button>

        <button
          onClick={() => setTab("memories")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded transition-all ${
            tab === "memories" ? "bg-[var(--accent-primary)]/20 text-[var(--accent-primary)] border border-[var(--accent-primary)]/50 font-bold" : "text-[var(--text-secondary)] hover:text-white"
          }`}
        >
          <Database className="w-3.5 h-3.5" />
          <span>DATABASE MEMORIES ({memories.length})</span>
        </button>
      </div>

      {/* Active Tab View */}
      <div className="glass-panel p-4 h-[350px] overflow-y-auto">
        {tab === "events" && (
          <div className="space-y-2">
            {events.length === 0 ? (
              <span className="text-[var(--text-muted)]">No live events recorded yet.</span>
            ) : (
              events.map((evt, idx) => (
                <div key={idx} className="p-2 bg-[var(--bg-secondary)] rounded border border-[var(--border)] font-mono text-[11px] space-y-0.5">
                  <div className="flex justify-between text-[var(--accent-primary)] font-bold">
                    <span>{evt.type}</span>
                    <span className="text-[var(--text-muted)] text-[10px]">{new Date((evt.timestamp || Date.now() / 1000) * 1000).toLocaleTimeString()}</span>
                  </div>
                  <pre className="text-[var(--text-secondary)] text-[10px] overflow-x-auto">
                    {JSON.stringify(evt, null, 2)}
                  </pre>
                </div>
              ))
            )}
          </div>
        )}

        {tab === "tools" && (
          <pre className="text-[var(--text-secondary)] text-[11px]">
            {JSON.stringify(tools, null, 2)}
          </pre>
        )}

        {tab === "memories" && (
          <pre className="text-[var(--text-secondary)] text-[11px]">
            {JSON.stringify(memories, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
};
