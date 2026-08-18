import React from "react";
import { Wrench, ShieldCheck } from "lucide-react";

export const Tools: React.FC = () => {
  const tools = [
    { name: "system_info", category: "SYSTEM", risk: "READ_ONLY", desc: "Read CPU, RAM, Disk system metrics", status: "Active" },
    { name: "take_screenshot", category: "VISION", risk: "LOW_RISK", desc: "Capture screen screenshot", status: "Active" },
    { name: "open_application", category: "SYSTEM", risk: "LOW_RISK", desc: "Open desktop application", status: "Active" },
    { name: "close_application", category: "SYSTEM", risk: "MODERATE", desc: "Close desktop application", status: "Active" },
    { name: "find_file", category: "FILESYSTEM", risk: "READ_ONLY", desc: "Search files on disk", status: "Active" },
    { name: "read_file", category: "FILESYSTEM", risk: "READ_ONLY", desc: "Read text file contents", status: "Active" },
    { name: "write_file", category: "FILESYSTEM", risk: "MODERATE", desc: "Write/Create text file", status: "Active" },
    { name: "run_command", category: "DEVELOPER", risk: "HIGH_RISK", desc: "Run terminal shell command", status: "Requires Confirmation" },
    { name: "search_web", category: "BROWSER", risk: "LOW_RISK", desc: "Search web using search engine", status: "Active" },
    { name: "set_volume", category: "MEDIA", risk: "LOW_RISK", desc: "Control audio volume", status: "Active" }
  ];

  return (
    <div className="h-full p-6 space-y-6 overflow-y-auto font-mono text-xs">
      <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
        <div className="flex items-center gap-2 text-sm font-bold text-[var(--accent-primary)] font-primary">
          <Wrench className="w-5 h-5 text-[var(--accent-primary)]" />
          <span>INSTALLED TOOL CAPABILITIES (15 TOOLS)</span>
        </div>
        <span className="text-[10px] text-[var(--success)]">SECURITY POLICY ACTIVE</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {tools.map((t, i) => (
          <div key={i} className="glass-panel p-4 space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-white font-bold font-primary text-xs">{t.name}</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                t.risk === "READ_ONLY" ? "bg-[var(--success)]/20 text-[var(--success)] border border-[var(--success)]/40" :
                t.risk === "HIGH_RISK" ? "bg-[var(--danger)]/20 text-[var(--danger)] border border-[var(--danger)]/40" :
                "bg-[var(--warning)]/20 text-[var(--warning)] border border-[var(--warning)]/40"
              }`}>
                {t.risk}
              </span>
            </div>
            <p className="text-[11px] text-[var(--text-secondary)]">{t.desc}</p>
            <div className="text-[10px] text-[var(--text-muted)] pt-1 border-t border-[var(--border)] flex justify-between">
              <span>CATEGORY: {t.category}</span>
              <span className="text-[var(--accent-primary)] font-bold">{t.status}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
