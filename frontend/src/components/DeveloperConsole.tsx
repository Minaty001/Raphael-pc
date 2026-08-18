import React, { useState } from "react";
import { WSEvent } from "../types";
import { Terminal, Cpu, Database, Eye } from "lucide-react";

interface Props {
  events: WSEvent[];
  tools: any[];
  memories: any[];
}

export const DeveloperConsole: React.FC<Props> = ({ events, tools, memories }) => {
  const [activeTab, setActiveTab] = useState<"events" | "tools" | "memories">("events");

  return (
    <div className="hud-card p-4 space-y-3">
      <div className="hud-header justify-between">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-purple-400" />
          <span>DEVELOPER & INSPECTOR CONSOLE</span>
        </div>

        {/* Tab switcher */}
        <div className="flex gap-1 text-[11px] font-mono">
          <button
            onClick={() => setActiveTab("events")}
            className={`px-2.5 py-1 rounded border transition-all ${
              activeTab === "events"
                ? "bg-purple-950 border-purple-500 text-purple-300 font-bold"
                : "border-slate-800 text-slate-500 hover:text-slate-300"
            }`}
          >
            EVENTS ({events.length})
          </button>
          <button
            onClick={() => setActiveTab("tools")}
            className={`px-2.5 py-1 rounded border transition-all ${
              activeTab === "tools"
                ? "bg-purple-950 border-purple-500 text-purple-300 font-bold"
                : "border-slate-800 text-slate-500 hover:text-slate-300"
            }`}
          >
            TOOLS ({tools.length})
          </button>
          <button
            onClick={() => setActiveTab("memories")}
            className={`px-2.5 py-1 rounded border transition-all ${
              activeTab === "memories"
                ? "bg-purple-950 border-purple-500 text-purple-300 font-bold"
                : "border-slate-800 text-slate-500 hover:text-slate-300"
            }`}
          >
            MEMORIES ({memories.length})
          </button>
        </div>
      </div>

      <div className="bg-slate-950 p-3 rounded border border-slate-800 h-48 overflow-y-auto font-mono text-[11px] space-y-1 text-slate-300">
        {activeTab === "events" && (
          events.length === 0 ? (
            <div className="text-slate-600">NO WEBSOCKET EVENTS CAPTURED</div>
          ) : (
            events.slice().reverse().map((ev, i) => (
              <div key={i} className="flex items-start gap-2 border-b border-slate-900 pb-1">
                <span className="text-slate-600 font-bold">{new Date(ev.timestamp * 1000).toLocaleTimeString()}</span>
                <span className="text-cyan-400 font-semibold">{ev.type}</span>
                <span className="text-slate-400 truncate">{JSON.stringify(ev)}</span>
              </div>
            ))
          )
        )}

        {activeTab === "tools" && (
          tools.map((t, i) => (
            <div key={i} className="p-1.5 border-b border-slate-900 flex justify-between">
              <div>
                <span className="text-amber-400 font-bold">{t.name}</span>
                <span className="text-slate-500 ml-2">({t.risk_level})</span>
                <p className="text-slate-400 text-[10px]">{t.description}</p>
              </div>
              <span className="text-slate-600">{t.parameters.join(", ")}</span>
            </div>
          ))
        )}

        {activeTab === "memories" && (
          memories.length === 0 ? (
            <div className="text-slate-600">NO PERSISTENT MEMORIES RECORDED</div>
          ) : (
            memories.map((m, i) => (
              <div key={i} className="p-1 border-b border-slate-900">
                <span className="text-emerald-400">[{m.category}]</span> {m.content}
                <span className="text-slate-600 ml-2">({(m.confidence * 100).toFixed(0)}% conf)</span>
              </div>
            ))
          )
        )}
      </div>
    </div>
  );
};
