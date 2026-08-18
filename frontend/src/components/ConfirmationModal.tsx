import React from "react";
import { SecurityConfirmationRequest } from "../types";
import { ShieldAlert, Check, X } from "lucide-react";

interface Props {
  request: SecurityConfirmationRequest | null;
  onRespond: (approved: boolean) => void;
}

export const ConfirmationModal: React.FC<Props> = ({ request, onRespond }) => {
  if (!request) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="hud-card max-w-md w-full p-6 space-y-4 border-amber-500/50 shadow-[0_0_30px_rgba(255,170,0,0.3)] animate-in fade-in zoom-in-95">
        <div className="flex items-center gap-3 text-amber-400 border-b border-amber-500/20 pb-3">
          <ShieldAlert className="w-6 h-6 animate-pulse" />
          <h3 className="font-display text-sm tracking-wider font-bold uppercase">
            PRIVILEGED ACTION CONFIRMATION
          </h3>
        </div>

        <div className="space-y-2 text-xs font-mono">
          <div className="text-slate-300">
            <span className="text-slate-500">TOOL: </span>
            <span className="text-cyan-400 font-bold">{request.tool_name}</span>
          </div>

          <div className="text-slate-300">
            <span className="text-slate-500">REASON: </span>
            <span className="text-amber-300">{request.reason}</span>
          </div>

          <div className="bg-slate-950 p-3 rounded border border-slate-800 text-[11px] text-slate-400 font-mono overflow-x-auto max-h-32">
            <pre>{JSON.stringify(request.args, null, 2)}</pre>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            onClick={() => onRespond(false)}
            className="flex items-center gap-1.5 px-4 py-2 rounded border border-rose-500/40 bg-rose-950/40 text-rose-300 hover:bg-rose-900/60 font-mono text-xs font-semibold transition-all"
          >
            <X className="w-4 h-4" />
            <span>DENY</span>
          </button>

          <button
            onClick={() => onRespond(true)}
            className="flex items-center gap-1.5 px-4 py-2 rounded border border-emerald-500/40 bg-emerald-950/40 text-emerald-300 hover:bg-emerald-900/60 font-mono text-xs font-semibold transition-all shadow-[0_0_15px_rgba(0,255,136,0.2)]"
          >
            <Check className="w-4 h-4" />
            <span>APPROVE</span>
          </button>
        </div>
      </div>
    </div>
  );
};
