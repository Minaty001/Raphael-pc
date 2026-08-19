import React, { useState } from "react";
import { Eye, Globe, ScanLine, BookOpen, AlertTriangle, Loader2 } from "lucide-react";
import { wsClient } from "../websocket";

interface ScreenResult {
  status: string;
  result?: {
    mode: string;
    visual_summary?: string;
    ocr_engine_available?: boolean;
    ocr_text?: string;
    ocr_word_count?: number;
    screenshot?: string;
    active_app?: string;
    window_title?: string;
  };
}

interface WebResult {
  status: string;
  result?: {
    url: string;
    title: string;
    text: string;
    word_count: number;
    links: string[];
    engine: string;
  };
  error?: string;
}

export const Vision: React.FC = () => {
  const [privacyMode, setPrivacyMode] = useState<"OFF" | "ON_DEMAND" | "SMART" | "CONTINUOUS">("ON_DEMAND");
  const [screen, setScreen] = useState<ScreenResult | null>(null);
  const [screenLoading, setScreenLoading] = useState(false);

  const [url, setUrl] = useState("");
  const [web, setWeb] = useState<WebResult | null>(null);
  const [webLoading, setWebLoading] = useState(false);

  const scanScreen = async () => {
    setScreenLoading(true);
    setScreen(null);
    const res = (await wsClient.executeTool("read_screen", { detail: "visual" })) as ScreenResult | null;
    setScreen(res);
    setScreenLoading(false);
  };

  const readWeb = async () => {
    if (!url.trim()) return;
    setWebLoading(true);
    setWeb(null);
    const res = (await wsClient.executeTool("read_webpage", { url: url.trim() })) as WebResult | null;
    setWeb(res);
    setWebLoading(false);
  };

  return (
    <div className="h-full p-6 space-y-6 overflow-y-auto font-mono text-xs">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
        <div className="flex items-center gap-2 text-sm font-bold text-[var(--accent-primary)] font-primary">
          <Eye className="w-5 h-5 text-[var(--accent-primary)]" />
          <span>DESKTOP VISION &amp; SCREEN PERCEPTION</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[var(--text-muted)]">PRIVACY MODE:</span>
          {["OFF", "ON_DEMAND", "SMART", "CONTINUOUS"].map((m) => (
            <button
              key={m}
              onClick={() => setPrivacyMode(m as any)}
              className={`px-2.5 py-1 rounded text-[10px] transition-all ${
                privacyMode === m
                  ? "bg-[var(--accent-primary)]/20 border border-[var(--accent-primary)] text-[var(--accent-primary)] font-bold"
                  : "bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:text-white"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Screen Perception Panel (real read_screen) */}
        <div className="glass-panel p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-bold text-[var(--accent-secondary)]">
              <ScanLine className="w-4 h-4" />
              <span>LIVE SCREEN ANALYSIS</span>
            </div>
            <button
              onClick={scanScreen}
              disabled={screenLoading}
              className="btn-ghost px-3 py-1.5 text-[11px] flex items-center gap-1.5 disabled:opacity-50"
            >
              {screenLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ScanLine className="w-3.5 h-3.5" />}
              {screenLoading ? "Scanning..." : "Scan Screen"}
            </button>
          </div>

          {!screen && !screenLoading && (
            <p className="text-[11px] text-[var(--text-muted)] italic">
              Click “Scan Screen” to capture the active window and (if a tesseract OCR engine is
              installed) extract on-screen text.
            </p>
          )}

          {screen && screen.result && (
            <div className="space-y-2 text-xs">
              <div className="p-2.5 bg-[var(--bg-secondary)] rounded border border-[var(--border)]">
                <span className="text-[var(--text-muted)] text-[10px]">APPLICATION:</span>
                <p className="text-white font-semibold">{screen.result.active_app || "Unknown"}</p>
              </div>
              <div className="p-2.5 bg-[var(--bg-secondary)] rounded border border-[var(--border)]">
                <span className="text-[var(--text-muted)] text-[10px]">WINDOW:</span>
                <p className="text-white">{screen.result.window_title || "—"}</p>
              </div>
              <div className="p-2.5 bg-[var(--bg-secondary)] rounded border border-[var(--border)]">
                <span className="text-[var(--text-muted)] text-[10px]">VISUAL SUMMARY:</span>
                <p className="text-[var(--accent-primary)]">{screen.result.visual_summary}</p>
              </div>
              {screen.result.ocr_engine_available ? (
                <div className="p-2.5 bg-[var(--bg-secondary)] rounded border border-[var(--border)] space-y-1">
                  <span className="text-[var(--text-muted)] text-[10px]">
                    EXTRACTED TEXT ({screen.result.ocr_word_count} words):
                  </span>
                  <p className="text-[11px] text-[var(--text-secondary)] whitespace-pre-wrap max-h-40 overflow-y-auto">
                    {screen.result.ocr_text}
                  </p>
                </div>
              ) : (
                <div className="flex items-start gap-2 p-2.5 bg-[var(--warning)]/10 rounded border border-[var(--warning)]/40">
                  <AlertTriangle className="w-4 h-4 text-[var(--warning)] shrink-0 mt-0.5" />
                  <p className="text-[11px] text-[var(--warning)]">
                    OCR engine not installed — only structural signal (app/window) is available.
                    Install <code>tesseract</code> + <code>pip install pytesseract</code> for full text.
                  </p>
                </div>
              )}
            </div>
          )}

          {screen && screen.status !== "success" && (
            <p className="text-[11px] text-[var(--danger)]">Screen scan failed: {(screen as any).error}</p>
          )}
        </div>

        {/* Web Reader Panel (real read_webpage) */}
        <div className="glass-panel p-4 space-y-3">
          <div className="flex items-center gap-2 text-xs font-bold text-[var(--accent-secondary)]">
            <Globe className="w-4 h-4" />
            <span>WEB READER</span>
          </div>

          <div className="flex gap-2">
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && readWeb()}
              placeholder="https://example.com"
              className="flex-1 bg-[var(--bg-secondary)] border border-[var(--border)] rounded px-3 py-2 text-[11px] text-white placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-primary)]"
            />
            <button
              onClick={readWeb}
              disabled={webLoading || !url.trim()}
              className="btn-ghost px-3 py-2 text-[11px] flex items-center gap-1.5 disabled:opacity-50"
            >
              {webLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <BookOpen className="w-3.5 h-3.5" />}
              Read
            </button>
          </div>

          {web && web.status === "success" && web.result && (
            <div className="space-y-2 text-xs">
              <div className="p-2.5 bg-[var(--bg-secondary)] rounded border border-[var(--border)]">
                <span className="text-[var(--text-muted)] text-[10px]">TITLE:</span>
                <p className="text-white font-semibold">{web.result.title}</p>
              </div>
              <div className="p-2.5 bg-[var(--bg-secondary)] rounded border border-[var(--border)]">
                <span className="text-[var(--text-muted)] text-[10px]">TEXT ({web.result.word_count} words):</span>
                <p className="text-[11px] text-[var(--text-secondary)] whitespace-pre-wrap max-h-40 overflow-y-auto">
                  {web.result.text}
                </p>
              </div>
              {web.result.links.length > 0 && (
                <div className="p-2.5 bg-[var(--bg-secondary)] rounded border border-[var(--border)] space-y-1">
                  <span className="text-[var(--text-muted)] text-[10px]">LINKS ({web.result.links.length}):</span>
                  <ul className="text-[11px] text-[var(--accent-primary)] space-y-0.5 max-h-32 overflow-y-auto">
                    {web.result.links.map((l, i) => (
                      <li key={i} className="truncate">• {l}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {web && web.status !== "success" && (
            <p className="text-[11px] text-[var(--danger)]">Read failed: {web.error}</p>
          )}

          {!web && !webLoading && (
            <p className="text-[11px] text-[var(--text-muted)] italic">
              Fetch a URL to extract its title, readable text, and links — no browser required.
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
