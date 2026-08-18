import React, { useState, useRef, useEffect } from "react";
import { ChatMessage } from "../types";
import { Send, Mic, MicOff, Bot, User, CheckCircle2, AlertCircle } from "lucide-react";

interface Props {
  messages: ChatMessage[];
  partialText: string;
  onSendMessage: (text: string) => void;
  isListening: boolean;
  onToggleListening: () => void;
}

export const ConversationPanel: React.FC<Props> = ({
  messages,
  partialText,
  onSendMessage,
  isListening,
  onToggleListening
}) => {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, partialText]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    onSendMessage(input.trim());
    setInput("");
  };

  return (
    <div className="hud-card flex flex-col h-full min-h-[380px] max-h-[550px] font-mono text-xs">
      {/* Header */}
      <div className="hud-header justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-cyan-400" />
          <span>CONVERSATION INTERFACE</span>
        </div>
        <span className="text-[10px] text-cyan-400/80">{messages.length} MESSAGES</span>
      </div>

      {/* Internal Scrollable Message History Area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 text-center space-y-2 py-8">
            <Bot className="w-8 h-8 text-cyan-500/40" />
            <p>Raphael Cognitive Assistant is ready.</p>
            <p className="text-[10px] text-slate-600">Speak or type a command like "show system info" or "search web for Raphael AI"</p>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex flex-col space-y-1 ${
                msg.sender === "user" ? "items-end" : "items-start"
              }`}
            >
              <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
                {msg.sender === "user" ? (
                  <>
                    <span>USER</span>
                    <User className="w-3 h-3 text-emerald-400" />
                  </>
                ) : (
                  <>
                    <Bot className="w-3 h-3 text-cyan-400" />
                    <span>RAPHAEL</span>
                  </>
                )}
                <span>• {new Date((msg.timestamp || Date.now() / 1000) * 1000).toLocaleTimeString()}</span>
              </div>

              <div
                className={`p-3 rounded-lg max-w-[85%] leading-relaxed ${
                  msg.sender === "user"
                    ? "bg-cyan-950/40 border border-cyan-500/30 text-cyan-100 rounded-tr-none"
                    : "bg-slate-900/80 border border-slate-800 text-slate-200 rounded-tl-none"
                }`}
              >
                <p className="whitespace-pre-wrap select-text">{msg.text}</p>

                {msg.toolResult && (
                  <div className="mt-2 pt-2 border-t border-slate-800 text-[10px] space-y-1">
                    <div className="flex items-center gap-1 text-emerald-400 font-bold">
                      <CheckCircle2 className="w-3 h-3" />
                      <span>ACTION RESULT ({msg.toolResult.action}):</span>
                    </div>
                    <pre className="p-1.5 bg-slate-950 rounded text-slate-300 overflow-x-auto">
                      {JSON.stringify(msg.toolResult.result || msg.toolResult, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {partialText && (
          <div className="flex flex-col items-start space-y-1">
            <span className="text-[10px] text-emerald-400 italic">LIVE STT TRANSCRIPT...</span>
            <div className="p-2.5 bg-emerald-950/40 border border-emerald-500/30 text-emerald-200 rounded-lg max-w-[80%] italic">
              {partialText}
            </div>
          </div>
        )}
      </div>

      {/* Fixed Command Input Form Bar */}
      <form onSubmit={handleSubmit} className="p-3 border-t border-cyan-500/20 bg-slate-950/60 shrink-0 flex items-center gap-2">
        <button
          type="button"
          onClick={onToggleListening}
          className={`p-2 rounded border transition-all shrink-0 ${
            isListening
              ? "bg-rose-950/80 border-rose-500/60 text-rose-300 animate-pulse"
              : "bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200"
          }`}
          title={isListening ? "Stop Listening" : "Start Voice Recording"}
        >
          {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
        </button>

        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Command input (e.g. 'show system info' or 'open browser')..."
          className="flex-1 bg-slate-900/90 border border-slate-800 rounded px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500/50"
        />

        <button
          type="submit"
          disabled={!input.trim()}
          className="px-3.5 py-2 bg-cyan-950/80 border border-cyan-500/40 text-cyan-300 rounded text-xs hover:bg-cyan-900/80 disabled:opacity-40 flex items-center gap-1.5 shrink-0"
        >
          <span>SEND</span>
          <Send className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
};
