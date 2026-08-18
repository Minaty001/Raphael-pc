import React from "react";
import { CharacterStage } from "../components/character/CharacterStage";
import { ChatMessage, RaphaelStateType, PageView, SystemMetrics } from "../types";
import { Bot, User, Sparkles, ArrowRight, Cpu, Brain, Eye, Wrench, MessageSquare, Activity } from "lucide-react";

interface HomeProps {
  state: RaphaelStateType;
  messages: ChatMessage[];
  metrics: SystemMetrics | null;
  onSendMessage: (text: string) => void;
  onNavigate: (page: PageView) => void;
}

const STATE_HINT: Record<string, string> = {
  idle: "What can I help with?",
  listening: "Listening to you...",
  thinking: "Thinking it through...",
  executing: "Executing your request...",
  speaking: "Speaking...",
  error: "Something went wrong.",
  offline: "Connection lost — retrying...",
};

const QUICK_ACTIONS: { label: string; icon: React.ReactNode; page: PageView }[] = [
  { label: "Chat", icon: <MessageSquare className="w-4 h-4" />, page: "chat" },
  { label: "Memory", icon: <Brain className="w-4 h-4" />, page: "memory" },
  { label: "Vision", icon: <Eye className="w-4 h-4" />, page: "vision" },
  { label: "Tools", icon: <Wrench className="w-4 h-4" />, page: "tools" },
  { label: "Activity", icon: <Activity className="w-4 h-4" />, page: "activity" },
];

const StatPill: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="hud-card px-4 py-3 flex flex-col gap-0.5 min-w-[120px]">
    <span className="text-[10px] font-mono uppercase tracking-widest text-[var(--text-muted)]">{label}</span>
    <span className="text-lg font-display font-bold text-[var(--accent-primary)]">{value}</span>
  </div>
);

export const Home: React.FC<HomeProps> = ({ state, messages, metrics, onSendMessage, onNavigate }) => {
  const cpu = metrics?.cpu_percent ?? 12;
  const ram = metrics?.memory_percent ?? 42;
  const disk = metrics?.disk_percent ?? 18;
  const recent = messages.slice(-4);

  const handleQuick = (text: string) => onSendMessage(text);

  return (
    <div className="h-full overflow-y-auto hud-grid">
      <div className="max-w-6xl mx-auto p-6 grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left: Hero character + status */}
        <div className="lg:col-span-1 flex flex-col items-center justify-start gap-4 rounded-lg border border-[var(--border)] bg-[var(--panel)] p-6 backdrop-blur-md">
          <CharacterStage className="w-full" />
          <h2 className="text-center font-display text-lg tracking-wide text-[var(--accent-primary)]">
            {STATE_HINT[state] ?? STATE_HINT.idle}
          </h2>
          <p className="text-center text-xs text-[var(--text-secondary)] max-w-xs">
            Raphael is your always-on cognitive desktop assistant. Ask anything, or use voice with{" "}
            <span className="font-mono text-[var(--accent-primary)]">Ctrl + Space</span>.
          </p>

          <div className="w-full flex items-center justify-between px-4 py-2 rounded-md bg-[var(--bg-secondary)] border border-[var(--border)] font-mono text-[11px]">
            <span className="text-[var(--text-muted)]">STATUS</span>
            <span className="uppercase tracking-widest font-bold text-[var(--accent-primary)]">{state}</span>
          </div>
        </div>

        {/* Right: Stats + activity + quick actions */}
        <div className="lg:col-span-2 flex flex-col gap-5">
          {/* Live system stats */}
          <div className="flex flex-wrap gap-3">
            <StatPill label="CPU" value={`${cpu.toFixed(0)}%`} />
            <StatPill label="Memory" value={`${ram.toFixed(0)}%`} />
            <StatPill label="Disk" value={`${disk.toFixed(0)}%`} />
            <StatPill label="Messages" value={`${messages.length}`} />
            <div className="flex-1 min-w-[160px] hud-card px-4 py-3 flex flex-col gap-1">
              <span className="text-[10px] font-mono uppercase tracking-widest text-[var(--text-muted)]">Open Loops</span>
              <div className="flex items-center gap-2">
                <span className="text-lg font-display font-bold text-[var(--warning)]">1</span>
                <span className="text-[11px] text-[var(--text-secondary)] truncate">WebSocket reconnect test</span>
                <button
                  onClick={() => onNavigate("goals")}
                  className="ml-auto text-[10px] text-[var(--accent-primary)] hover:underline flex items-center gap-1"
                >
                  VIEW <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          </div>

          {/* Proactive initiative banner */}
          <div className="hud-card p-3 flex items-center justify-between font-mono text-xs text-[var(--warning)]">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[var(--warning)] shrink-0" />
              <span>RAPHAEL INITIATIVE: 1 open loop detected for WebSocket reconnect test.</span>
            </div>
            <button
              onClick={() => onNavigate("goals")}
              className="text-[10px] text-[var(--accent-primary)] hover:underline flex items-center gap-1 shrink-0"
            >
              <span>GOALS</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          {/* Quick actions */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {QUICK_ACTIONS.map((q) => (
              <button
                key={q.label}
                onClick={() => onNavigate(q.page)}
                className="hud-card flex flex-col items-center justify-center gap-2 py-4 hover:border-[var(--accent-primary)]/50 hover:shadow-[0_0_18px_var(--glow)] transition-all group"
              >
                <span className="text-[var(--accent-primary)] group-hover:scale-110 transition-transform">{q.icon}</span>
                <span className="text-[11px] font-mono tracking-wider text-[var(--text-secondary)] group-hover:text-white">
                  {q.label}
                </span>
              </button>
            ))}
          </div>

          {/* Recent conversation */}
          <div className="hud-card flex-1 p-4 flex flex-col min-h-[200px]">
            <div className="hud-header justify-between border-b border-[var(--border)] pb-2 mb-3">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-[var(--accent-primary)]" />
                <span>RECENT ACTIVITY</span>
              </div>
              <button
                onClick={() => onNavigate("chat")}
                className="text-[10px] text-[var(--accent-primary)] hover:underline"
              >
                OPEN CHAT →
              </button>
            </div>

            {recent.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center text-[var(--text-muted)] gap-2 py-6">
                <Bot className="w-8 h-8 text-[var(--accent-primary)]/40" />
                <p className="font-primary text-sm text-[var(--text-secondary)]">Raphael is active and ready.</p>
                <p className="text-[11px] font-mono">
                  Try: &quot;Show system info&quot;, &quot;What am I working on?&quot;, &quot;Search web for Raphael AI&quot;
                </p>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto space-y-3">
                {recent.map((msg) => (
                  <div key={msg.id} className={`flex flex-col space-y-1 ${msg.sender === "user" ? "items-end" : "items-start"}`}>
                    <div className="flex items-center gap-1.5 text-[10px] text-[var(--text-muted)]">
                      {msg.sender === "user" ? (
                        <>
                          <span>YOU</span>
                          <User className="w-3 h-3 text-[var(--success)]" />
                        </>
                      ) : (
                        <>
                          <Bot className="w-3 h-3 text-[var(--accent-primary)]" />
                          <span>RAPHAEL</span>
                        </>
                      )}
                    </div>
                    <div
                      className={`p-3 rounded-lg max-w-[88%] font-primary text-xs ${
                        msg.sender === "user"
                          ? "bg-[var(--accent-primary)]/15 border border-[var(--accent-primary)]/40 text-cyan-100 rounded-tr-none"
                          : "bg-[var(--bg-secondary)] border border-[var(--border)] text-[var(--text-primary)] rounded-tl-none"
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{msg.text}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
