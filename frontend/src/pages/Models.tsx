import React from "react";
import { Cpu, ArrowRight } from "lucide-react";

export const Models: React.FC = () => {
  const models = [
    { role: "Conversation LLM", provider: "Ollama / OpenRouter", model: "Llama-3.3-70b-instruct", status: "Active", latency: "620ms" },
    { role: "Vision Perception", provider: "Local Vision / OCR", model: "Tesseract / Screenshot OCR", status: "Active", latency: "820ms" },
    { role: "Vector Embedding", provider: "Local Embedding", model: "MiniLM-L6-v2", status: "Active", latency: "45ms" },
    { role: "Voice STT & TTS", provider: "Sherpa-ONNX Local", model: "VAD + ONNX STT", status: "Active", latency: "380ms" }
  ];

  return (
    <div className="h-full p-6 space-y-6 overflow-y-auto font-mono text-xs">
      <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
        <div className="flex items-center gap-2 text-sm font-bold text-[var(--accent-primary)] font-primary">
          <Cpu className="w-5 h-5 text-[var(--accent-primary)]" />
          <span>ACTIVE BRAIN MODELS & MODEL ROUTING</span>
        </div>
        <span className="text-[10px] text-[var(--success)]">ALL PROVIDERS OPERATIONAL</span>
      </div>

      {/* Model Router Flow Diagram */}
      <div className="glass-panel p-4 space-y-3">
        <span className="text-[10px] text-[var(--accent-primary)] font-bold">MODEL ROUTER FLOW</span>
        <div className="flex flex-wrap items-center gap-2 text-xs font-bold text-center">
          <span className="px-3 py-2 bg-[var(--bg-secondary)] border border-[var(--border)] rounded text-white">USER REQUEST</span>
          <ArrowRight className="w-4 h-4 text-[var(--accent-primary)]" />
          <span className="px-3 py-2 bg-[var(--bg-secondary)] border border-[var(--border)] rounded text-white">INTENT CLASSIFIER</span>
          <ArrowRight className="w-4 h-4 text-[var(--accent-primary)]" />
          <span className="px-3 py-2 bg-[var(--accent-primary)]/20 border border-[var(--accent-primary)] rounded text-[var(--accent-primary)]">MODEL ROUTER</span>
          <ArrowRight className="w-4 h-4 text-[var(--accent-primary)]" />
          <div className="flex gap-2">
            <span className="px-2.5 py-1.5 bg-[var(--success)]/20 border border-[var(--success)] text-[var(--success)] rounded text-[10px]">Fast Intent</span>
            <span className="px-2.5 py-1.5 bg-[var(--warning)]/20 border border-[var(--warning)] text-[var(--warning)] rounded text-[10px]">Vision OCR</span>
            <span className="px-2.5 py-1.5 bg-[var(--accent-secondary)]/20 border border-[var(--accent-secondary)] text-[var(--accent-secondary)] rounded text-[10px]">Reasoning LLM</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {models.map((m, i) => (
          <div key={i} className="glass-panel p-4 space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-white font-bold font-primary text-xs">{m.role}</span>
              <span className="text-[var(--success)] font-bold text-[10px]">{m.status}</span>
            </div>
            <div className="text-[11px] text-[var(--text-secondary)] space-y-1">
              <div>Provider: <span className="text-white">{m.provider}</span></div>
              <div>Model: <span className="text-[var(--accent-primary)]">{m.model}</span></div>
              <div>Latency: <span className="text-[var(--warning)]">{m.latency}</span></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
