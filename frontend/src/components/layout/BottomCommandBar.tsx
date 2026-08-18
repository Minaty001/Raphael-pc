import React, { useEffect, useState } from "react";
import { Mic, MicOff, Send, Command } from "lucide-react";

interface BottomCommandBarProps {
  onSendMessage: (text: string) => void;
  isListening: boolean;
  onToggleListening: () => void;
  partialText: string;
}

export const BottomCommandBar: React.FC<BottomCommandBarProps> = ({
  onSendMessage,
  isListening,
  onToggleListening,
  partialText,
}) => {
  const [text, setText] = useState("");

  // Global Ctrl+Space / Cmd+Space to toggle voice
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.code === "Space") {
        e.preventDefault();
        onToggleListening();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onToggleListening]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    onSendMessage(text.trim());
    setText("");
  };

  return (
    <div className="shrink-0 flex flex-col gap-2 p-3 border-t border-[var(--border)] bg-[#070c14]/95 backdrop-blur z-40 select-none">
      {partialText && (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-[var(--success)]/10 border border-[var(--success)]/30 rounded-md text-xs font-mono text-[var(--success)] animate-pulse">
          <Mic className="w-3.5 h-3.5" />
          <span className="truncate">LISTENING: &quot;{partialText}&quot;</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex items-center gap-2">
        <button
          type="button"
          onClick={onToggleListening}
          className={`p-3 rounded-md border transition-all shrink-0 ${
            isListening
              ? "bg-[var(--danger)]/20 border-[var(--danger)] text-[var(--danger)] animate-pulse shadow-[0_0_12px_var(--danger)]"
              : "bg-[var(--bg-secondary)] border-[var(--border)] text-[var(--text-secondary)] hover:text-white"
          }`}
          title={isListening ? "Stop Listening (Ctrl+Space)" : "Talk to Raphael (Ctrl+Space)"}
        >
          {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
        </button>

        <div className="relative flex-1">
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={isListening ? "Listening..." : "Talk to Raphael or type a command..."}
            className="w-full bg-[var(--bg-secondary)] border border-[var(--border)] rounded-md px-4 py-3 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-primary)]/60 font-primary"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 hidden md:flex items-center gap-1 text-[10px] font-mono text-[var(--text-muted)] border border-[var(--border)] px-2 py-0.5 rounded">
            <Command className="w-2.5 h-2.5" />
            <span>Ctrl + Space</span>
          </div>
        </div>

        <button
          type="submit"
          disabled={!text.trim()}
          className="px-5 py-3 bg-[var(--accent-primary)]/20 border border-[var(--accent-primary)]/50 text-[var(--accent-primary)] rounded-md font-mono text-xs font-bold hover:bg-[var(--accent-primary)]/30 disabled:opacity-30 transition-all flex items-center gap-1.5 shrink-0"
        >
          <span>SEND</span>
          <Send className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
};
