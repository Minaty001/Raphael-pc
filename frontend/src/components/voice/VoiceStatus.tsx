import React from "react";
import { AudioStateType } from "../../types";

/**
 * VoiceStatus — privacy-aware voice indicator (Sections 35 / 68).
 * Clearly separates "wake listening" (low-power, mic open for wake only)
 * from "command listening" (actively capturing speech). These are NOT the same.
 */

const VOICE_META: Record<AudioStateType, { label: string; color: string; pulse: boolean }> = {
  AUDIO_IDLE: { label: "Idle", color: "#526372", pulse: false },
  WAKE_LISTENING: { label: "Wake Listening", color: "#56d9ff", pulse: true },
  WAKE_DETECTED: { label: "Wake Detected", color: "#6f8cff", pulse: true },
  COMMAND_LISTENING: { label: "Recording Command", color: "#4ce09a", pulse: true },
  PROCESSING: { label: "Processing", color: "#6f8cff", pulse: false },
  SPEAKING: { label: "Speaking", color: "#56d9ff", pulse: false },
  INTERRUPTED: { label: "Interrupted", color: "#f4c95d", pulse: true },
  PAUSED: { label: "Voice Paused", color: "#90a0aa", pulse: false },
  ERROR: { label: "Voice Error", color: "#ff647c", pulse: false },
};

export const VoiceStatus: React.FC<{ audioState: AudioStateType }> = ({ audioState }) => {
  const meta = VOICE_META[audioState] ?? VOICE_META.AUDIO_IDLE;
  const isCapture = audioState === "COMMAND_LISTENING";

  return (
    <div className="fixed bottom-24 right-4 z-30 flex items-center gap-2 px-3 py-1.5 rounded-full border border-[var(--border)] bg-[#070c14]/90 backdrop-blur select-none">
      <span
        className={`w-2.5 h-2.5 rounded-full ${meta.pulse ? "animate-pulse" : ""}`}
        style={{ background: meta.color, boxShadow: `0 0 8px ${meta.color}` }}
      />
      <span className="text-[10px] font-mono uppercase tracking-widest" style={{ color: meta.color }}>
        {meta.label}
      </span>
      {/* Explicit privacy note so the user knows what is being captured (Section 35) */}
      <span className="text-[9px] font-mono text-[var(--text-muted)] hidden md:inline">
        {isCapture ? "capturing speech" : "wake only"}
      </span>
    </div>
  );
};
