import React from "react";
import { RaphaelStateType } from "../../types";

interface RaphaelOrbProps {
  state: RaphaelStateType;
  intensity?: number;
  size?: number;
}

export const RaphaelOrb: React.FC<RaphaelOrbProps> = ({ state, intensity = 1, size = 180 }) => {
  const getColorScheme = () => {
    switch (state) {
      case "listening":
        return { primary: "#4ce09a", secondary: "#10b981", glow: "rgba(76, 224, 154, 0.45)" };
      case "thinking":
        return { primary: "#6f8cff", secondary: "#a855f7", glow: "rgba(111, 140, 255, 0.45)" };
      case "executing":
        return { primary: "#f4c95d", secondary: "#f59e0b", glow: "rgba(244, 201, 93, 0.45)" };
      case "speaking":
        return { primary: "#56d9ff", secondary: "#00f0ff", glow: "rgba(86, 217, 255, 0.45)" };
      case "error":
        return { primary: "#ff647c", secondary: "#f43f5e", glow: "rgba(255, 100, 124, 0.45)" };
      case "offline":
        return { primary: "#526372", secondary: "#64748b", glow: "rgba(82, 99, 114, 0.25)" };
      case "idle":
      default:
        return { primary: "#56d9ff", secondary: "#6f8cff", glow: "rgba(86, 217, 255, 0.35)" };
    }
  };

  const color = getColorScheme();
  const animClass = state === "thinking" ? "orb-spin-fast" : state === "executing" ? "orb-spin" : "orb-breathe";

  return (
    <div className="relative flex items-center justify-center select-none" style={{ width: size, height: size }}>
      {/* Outer glowing ring */}
      <svg className={`absolute inset-0 w-full h-full ${animClass}`} viewBox="0 0 100 100">
        <circle
          cx="50"
          cy="50"
          r="44"
          fill="none"
          stroke={color.primary}
          strokeWidth="1.5"
          strokeDasharray={state === "executing" ? "60 10 20 10" : "180 30"}
          opacity="0.85"
        />
        <circle
          cx="50"
          cy="50"
          r="38"
          fill="none"
          stroke={color.secondary}
          strokeWidth="1"
          strokeDasharray="4 6"
          opacity="0.6"
        />
        {/* tick marks */}
        {Array.from({ length: 12 }).map((_, i) => {
          const angle = (i * 30 * Math.PI) / 180;
          const x1 = 50 + 47 * Math.cos(angle);
          const y1 = 50 + 47 * Math.sin(angle);
          const x2 = 50 + 50 * Math.cos(angle);
          const y2 = 50 + 50 * Math.sin(angle);
          return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke={color.primary} strokeWidth="0.6" opacity="0.4" />;
        })}
      </svg>

      {/* Core */}
      <div
        className="w-[50%] h-[50%] rounded-full transition-all duration-500 flex items-center justify-center"
        style={{
          background: `radial-gradient(circle, ${color.primary} 0%, ${color.secondary} 70%, transparent 100%)`,
          boxShadow: `0 0 32px 8px ${color.glow}`,
          transform: state === "listening" ? "scale(1.15)" : "scale(1.0)",
          opacity: intensity,
        }}
      >
        <div className="w-[30%] h-[30%] rounded-full bg-white/90 shadow-[0_0_12px_#ffffff]" />
      </div>

      {/* State label */}
      <div className="absolute -bottom-6 text-center font-mono text-[10px] tracking-[0.25em] uppercase text-slate-400">
        <span className="font-bold font-display tracking-wider" style={{ color: color.primary }}>
          {state}
        </span>
      </div>
    </div>
  );
};
