import React from "react";
import { ToolExecutionRecord } from "../types";
import { Wrench, CheckCircle2, XCircle, AlertTriangle } from "lucide-react";

interface Props {
  tools: ToolExecutionRecord[];
}

export const ToolStreamPanel: React.FC<Props> = ({ tools }) => {
  return (
    <div className="hud-card p-4 space-y-3">
      <div className="hud-header justify-between">
        <div className="flex items-center gap-2">
          <Wrench className="w-4 h-4 text-amber-400" />
          <span>DESKTOP ACTION STREAM</span>
        </div>
        <span className="font-mono text-[10px] text-slate-500">{tools.length} EXECUTIONS</span>
      </div>

      <div className="space-y-2 max-h-[220px] overflow-y-auto font-mono text-xs pr-1">
        {tools.length === 0 && (
          <div className="text-center text-slate-600 py-6">
            NO DESKTOP ACTIONS EXECUTED YET
          </div>
        )}

        {tools.map((t) => (
          <div
            key={t.id}
            className="p-2.5 bg-slate-900/60 rounded border border-slate-800 flex items-center justify-between gap-2"
          >
            <div className="flex items-center gap-2 overflow-hidden">
              {t.status === "success" && <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />}
              {t.status === "failed" && <XCircle className="w-4 h-4 text-rose-400 shrink-0" />}
              {t.status === "denied" && <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />}
              {t.status === "started" && (
                <div className="w-3.5 h-3.5 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin shrink-0" />
              )}

              <div className="truncate">
                <span className="text-slate-200 font-semibold">{t.action}</span>
                {t.error && <span className="text-rose-400 text-[11px] block truncate">{t.error}</span>}
              </div>
            </div>

            <div className="text-right shrink-0">
              <span className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-bold ${
                t.status === "success" ? "bg-emerald-950 text-emerald-300 border border-emerald-800" :
                t.status === "failed" ? "bg-rose-950 text-rose-300 border border-rose-800" :
                "bg-amber-950 text-amber-300 border border-amber-800"
              }`}>
                {t.status}
              </span>
              {t.duration_ms !== undefined && (
                <span className="text-slate-500 text-[10px] block mt-0.5">{t.duration_ms}ms</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
