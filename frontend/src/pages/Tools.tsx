import React, { useEffect, useState } from "react";
import { Wrench, ShieldCheck } from "lucide-react";
import { wsClient } from "../websocket";

interface ToolInfo {
  name: string;
  description?: string;
  risk_level?: string;
  category?: string;
}

const riskClass = (risk?: string) => {
  if (risk === "READ_ONLY" || risk === "LOW_RISK")
    return "bg-[var(--success)]/20 text-[var(--success)] border border-[var(--success)]/40";
  if (risk === "HIGH_RISK")
    return "bg-[var(--danger)]/20 text-[var(--danger)] border border-[var(--danger)]/40";
  return "bg-[var(--warning)]/20 text-[var(--warning)] border border-[var(--warning)]/40";
};

export const Tools: React.FC = () => {
  const [tools, setTools] = useState<ToolInfo[] | null>(null);

  useEffect(() => {
    wsClient.rest<ToolInfo[]>("/api/tools").then((data) => data && setTools(data)).catch(() => setTools([]));
  }, []);

  return (
    <div className="h-full p-6 space-y-6 overflow-y-auto font-mono text-xs">
      <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
        <div className="flex items-center gap-2 text-sm font-bold text-[var(--accent-primary)] font-primary">
          <Wrench className="w-5 h-5 text-[var(--accent-primary)]" />
          <span>
            INSTALLED TOOL CAPABILITIES (
            {tools ? `${tools.length} TOOLS` : "LOADING…"})
          </span>
        </div>
        <span className="text-[10px] text-[var(--success)]">SECURITY POLICY ACTIVE</span>
      </div>

      {!tools && (
        <p className="text-[11px] text-[var(--text-muted)] italic">Loading tools from runtime…</p>
      )}

      {tools && tools.length === 0 && (
        <p className="text-[11px] text-[var(--text-muted)] italic">No tools registered.</p>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {tools?.map((t) => (
          <div key={t.name} className="glass-panel p-4 space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-white font-bold font-primary text-xs">{t.name}</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${riskClass(t.risk_level)}`}>
                {t.risk_level ?? "UNKNOWN"}
              </span>
            </div>
            <p className="text-[11px] text-[var(--text-secondary)]">{t.description || "—"}</p>
            <div className="text-[10px] text-[var(--text-muted)] pt-1 border-t border-[var(--border)] flex justify-between">
              <span>CATEGORY: {t.category ?? "—"}</span>
              <span className="text-[var(--accent-primary)] font-bold">Active</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
