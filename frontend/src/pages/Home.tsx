import React from "react";
import { RaphaelOrb } from "../components/brain/RaphaelOrb";
import { ChatMessage, RaphaelStateType, PageView } from "../types";
import { Bot, User, Sparkles, CheckCircle2, ArrowRight } from "lucide-react";

interface HomeProps {
  state: RaphaelStateType;
  messages: ChatMessage[];
  onSendMessage: (text: string) => void;
  onNavigate: (page: PageView) => void;
}

export const Home: React.FC<HomeProps> = ({
  state,
  messages,
  onSendMessage,
  onNavigate
}) => {
  return (
    <div className="h-full flex flex-col items-center justify-between p-6 space-y-6 overflow-y-auto">
      {/* Central Raphael Orb Visualizer */}
      <div className="flex flex-col items-center justify-center space-y-4 pt-4 shrink-0">
        <RaphaelOrb state={state} size={180} />
        <h2 className="text-sm font-mono tracking-widest text-[var(--accent-primary)] pt-4">
          "What can I help with?"
        </h2>
      </div>

      {/* Proactive Initiatives Banner */}
      <div className="w-full max-w-2xl glass-panel p-3 flex items-center justify-between font-mono text-xs text-[var(--warning)] shrink-0">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-[var(--warning)] shrink-0" />
          <span>RAPHAEL INITIATIVE: 1 open loop detected for WebSocket reconnect test.</span>
        </div>
        <button
          onClick={() => onNavigate("goals")}
          className="text-[10px] text-[var(--accent-primary)] hover:underline flex items-center gap-1 shrink-0"
        >
          <span>VIEW GOALS</span>
          <ArrowRight className="w-3 h-3" />
        </button>
      </div>

      {/* Conversation Stream Preview */}
      <div className="w-full max-w-2xl flex-1 glass-panel p-4 overflow-y-auto space-y-3 font-mono text-xs min-h-[220px]">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center text-[var(--text-muted)] space-y-2 py-6">
            <Bot className="w-8 h-8 text-[var(--accent-primary)]/40" />
            <p className="font-primary text-sm text-[var(--text-secondary)]">Raphael Cognitive Assistant is active.</p>
            <p className="text-[11px]">Try saying "Show system info", "What am I working on?", or "Search web for Raphael AI".</p>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex flex-col space-y-1 ${msg.sender === "user" ? "items-end" : "items-start"}`}
            >
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
                {msg.toolResult && (
                  <div className="mt-2 pt-2 border-t border-[var(--border)] font-mono text-[10px] space-y-1">
                    <div className="flex items-center gap-1 text-[var(--success)] font-bold">
                      <CheckCircle2 className="w-3 h-3" />
                      <span>{msg.toolResult.action} Completed</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
