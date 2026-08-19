import React, { useState, useEffect } from "react";
import { Settings as SettingsIcon, Shield, Sliders, Mic, Eye, Brain, Cloud, Sparkles } from "lucide-react";
import { wsClient } from "../websocket";

export const SettingsPage: React.FC = () => {
  const [autonomy, setAutonomy] = useState(2);
  const [mic, setMic] = useState(true);
  const [screen, setScreen] = useState(true);
  const [memory, setMemory] = useState(true);
  const [cloud, setCloud] = useState(true);
  const [proactive, setProactive] = useState(true);

  const [llm, setLlm] = useState<{ primary_provider: string; groq_model: string; groq_free_models: string[]; providers: string[] }>({
    primary_provider: "groq",
    groq_model: "llama-3.3-70b-versatile",
    groq_free_models: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it"],
    providers: ["groq", "ollama", "openrouter", "mock"],
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    wsClient.rest<any>("/api/config/llm")
      .then((data) => data && setLlm(data))
      .catch(() => {});
  }, []);

  const applyLlm = async (patch: Partial<{ provider: string; groq_model: string }>) => {
    setSaving(true);
    try {
      const data = await wsClient.rest<any>("/api/config/llm", "POST", patch);
      if (data) {
        setLlm((p) => ({ ...p, primary_provider: data.primary_provider, groq_model: data.groq_model }));
      }
    } finally {
      setSaving(false);
    }
  };

  const autonomyLevels = [
    "Level 0: Chat Only",
    "Level 1: Suggestions",
    "Level 2: Safe Actions (Default)",
    "Level 3: Routine Automation",
    "Level 4: Proactive Assistance",
    "Level 5: High Autonomy"
  ];

  return (
    <div className="h-full p-6 space-y-6 overflow-y-auto font-mono text-xs">
      <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
        <div className="flex items-center gap-2 text-sm font-bold text-[var(--accent-primary)] font-primary">
          <SettingsIcon className="w-5 h-5 text-[var(--accent-primary)]" />
          <span>RAPHAEL SYSTEM CONFIGURATION & PRIVACY</span>
        </div>
        <span className="text-[10px] text-[var(--success)]">SECURITY POLICIES ENFORCED</span>
      </div>

      {/* Autonomy Level Slider */}
      <div className="glass-panel p-5 space-y-3">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-2 font-bold text-white font-primary text-xs">
            <Sliders className="w-4 h-4 text-[var(--accent-primary)]" /> AUTONOMY LEVEL
          </span>
          <span className="text-[var(--accent-primary)] font-bold text-xs">{autonomyLevels[autonomy]}</span>
        </div>

        <input
          type="range"
          min="0"
          max="5"
          step="1"
          value={autonomy}
          onChange={(e) => setAutonomy(parseInt(e.target.value))}
          className="w-full h-2 bg-[var(--bg-secondary)] rounded-lg appearance-none cursor-pointer accent-[var(--accent-primary)]"
        />

        <div className="flex justify-between text-[10px] text-[var(--text-muted)]">
          <span>Level 0 (Chat)</span>
          <span>Level 5 (High Autonomy)</span>
        </div>
      </div>

      {/* Privacy & Permission Toggles */}
      <div className="glass-panel p-5 space-y-4">
        <div className="flex items-center gap-2 font-bold text-white font-primary text-xs border-b border-[var(--border)] pb-2">
          <Shield className="w-4 h-4 text-[var(--success)]" /> PRIVACY & PERMISSION CONTROLS
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex items-center justify-between p-3 bg-[var(--bg-secondary)] rounded border border-[var(--border)]">
            <span className="flex items-center gap-2 text-slate-200">
              <Mic className="w-4 h-4 text-[var(--accent-primary)]" /> Microphone Monitoring
            </span>
            <button
              onClick={() => setMic(!mic)}
              className={`px-3 py-1 rounded text-xs font-bold transition-all ${
                mic ? "bg-[var(--success)]/20 border border-[var(--success)] text-[var(--success)]" : "bg-[var(--danger)]/20 border border-[var(--danger)] text-[var(--danger)]"
              }`}
            >
              {mic ? "ON" : "OFF"}
            </button>
          </div>

          <div className="flex items-center justify-between p-3 bg-[var(--bg-secondary)] rounded border border-[var(--border)]">
            <span className="flex items-center gap-2 text-slate-200">
              <Eye className="w-4 h-4 text-[var(--accent-primary)]" /> Screen Awareness
            </span>
            <button
              onClick={() => setScreen(!screen)}
              className={`px-3 py-1 rounded text-xs font-bold transition-all ${
                screen ? "bg-[var(--success)]/20 border border-[var(--success)] text-[var(--success)]" : "bg-[var(--danger)]/20 border border-[var(--danger)] text-[var(--danger)]"
              }`}
            >
              {screen ? "ON DEMAND" : "OFF"}
            </button>
          </div>

          <div className="flex items-center justify-between p-3 bg-[var(--bg-secondary)] rounded border border-[var(--border)]">
            <span className="flex items-center gap-2 text-slate-200">
              <Brain className="w-4 h-4 text-[var(--accent-primary)]" /> 5-Tier Memory
            </span>
            <button
              onClick={() => setMemory(!memory)}
              className={`px-3 py-1 rounded text-xs font-bold transition-all ${
                memory ? "bg-[var(--success)]/20 border border-[var(--success)] text-[var(--success)]" : "bg-[var(--danger)]/20 border border-[var(--danger)] text-[var(--danger)]"
              }`}
            >
              {memory ? "SELECTIVE" : "OFF"}
            </button>
          </div>

          <div className="flex items-center justify-between p-3 bg-[var(--bg-secondary)] rounded border border-[var(--border)]">
            <span className="flex items-center gap-2 text-slate-200">
              <Cloud className="w-4 h-4 text-[var(--accent-primary)]" /> Cloud AI Providers
            </span>
            <button
              onClick={() => setCloud(!cloud)}
              className={`px-3 py-1 rounded text-xs font-bold transition-all ${
                cloud ? "bg-[var(--success)]/20 border border-[var(--success)] text-[var(--success)]" : "bg-[var(--danger)]/20 border border-[var(--danger)] text-[var(--danger)]"
              }`}
            >
              {cloud ? "ALLOWED" : "OFFLINE ONLY"}
            </button>
          </div>

          <div className="flex items-center justify-between p-3 bg-[var(--bg-secondary)] rounded border border-[var(--border)] md:col-span-2">
            <span className="flex items-center gap-2 text-slate-200">
              <Sparkles className="w-4 h-4 text-[var(--warning)]" /> Proactive Assistant Engine
            </span>
            <button
              onClick={() => setProactive(!proactive)}
              className={`px-3 py-1 rounded text-xs font-bold transition-all ${
                proactive ? "bg-[var(--success)]/20 border border-[var(--success)] text-[var(--success)]" : "bg-[var(--danger)]/20 border border-[var(--danger)] text-[var(--danger)]"
              }`}
            >
              {proactive ? "ON" : "OFF"}
            </button>
          </div>
        </div>
      </div>

      {/* LLM Provider (Groq / Ollama / OpenRouter / Mock) */}
      <div className="glass-panel p-5 space-y-4">
        <div className="flex items-center gap-2 font-bold text-white font-primary text-xs border-b border-[var(--border)] pb-2">
          <Cloud className="w-4 h-4 text-[var(--accent-primary)]" /> LLM PROVIDER (GROQ FREE MODELS)
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <span className="text-[10px] text-[var(--text-muted)] uppercase">Active Provider</span>
            <select
              value={llm.primary_provider}
              disabled={saving}
              onChange={(e) => applyLlm({ provider: e.target.value })}
              className="w-full bg-[var(--bg-secondary)] border border-[var(--border)] rounded px-2 py-1.5 text-slate-200 text-xs"
            >
              {llm.providers.map((p) => (
                <option key={p} value={p}>{p.toUpperCase()}</option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <span className="text-[10px] text-[var(--text-muted)] uppercase">Groq Model</span>
            <select
              value={llm.groq_model}
              disabled={saving || llm.primary_provider !== "groq"}
              onChange={(e) => applyLlm({ groq_model: e.target.value })}
              className="w-full bg-[var(--bg-secondary)] border border-[var(--border)] rounded px-2 py-1.5 text-slate-200 text-xs disabled:opacity-40"
            >
              {llm.groq_free_models.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
        </div>
        <p className="text-[10px] text-[var(--text-muted)]">
          Groq API key is loaded from a local .env file (never committed). Free models: llama-3.3-70b, llama-3.1-8b-instant, gemma2-9b-it, mixtral-8x7b, llama3-8b/70b.
        </p>
      </div>
    </div>
  );
};
