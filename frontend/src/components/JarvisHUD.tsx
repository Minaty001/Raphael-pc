import React, { useEffect, useRef } from "react";
import { AssistantState } from "../types";

interface Props {
  state: AssistantState;
  isListening: boolean;
}

export const JarvisHUD: React.FC<Props> = ({ state, isListening }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let rotation = 0;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const cx = canvas.width / 2;
      const cy = canvas.height / 2;
      const radius = 55;

      rotation += 0.015;

      // Color scheme based on state
      let primaryColor = "#00f0ff"; // Cyan IDLE
      if (state === "LISTENING" || isListening) primaryColor = "#10b981"; // Emerald
      else if (state === "THINKING" || state === "PLANNING") primaryColor = "#a855f7"; // Purple
      else if (state === "RETRIEVING_MEMORY" || state === "UNDERSTANDING") primaryColor = "#3b82f6"; // Blue
      else if (state === "EXECUTING" || state === "VERIFYING") primaryColor = "#f59e0b"; // Amber
      else if (state === "SPEAKING") primaryColor = "#06b6d4"; // Cyan-blue
      else if (state === "LEARNING" || state === "REFLECTING") primaryColor = "#ec4899"; // Pink
      else if (state === "ERROR") primaryColor = "#f43f5e"; // Rose
      else if (state === "OFFLINE") primaryColor = "#64748b"; // Slate

      // Outer rotating arc
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(rotation);
      ctx.beginPath();
      ctx.arc(0, 0, radius, 0, Math.PI * 1.4);
      ctx.strokeStyle = primaryColor;
      ctx.lineWidth = 2.5;
      ctx.shadowBlur = 12;
      ctx.shadowColor = primaryColor;
      ctx.stroke();
      ctx.restore();

      // Inner counter-rotating ring
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(-rotation * 1.5);
      ctx.beginPath();
      ctx.arc(0, 0, radius - 12, 0, Math.PI * 1.2);
      ctx.strokeStyle = primaryColor;
      ctx.lineWidth = 1.2;
      ctx.setLineDash([5, 5]);
      ctx.stroke();
      ctx.restore();

      // Core pulsing glow
      const pulse = Math.sin(Date.now() / 250) * 3;
      ctx.beginPath();
      ctx.arc(cx, cy, radius - 28 + pulse, 0, Math.PI * 2);
      ctx.fillStyle = primaryColor;
      ctx.globalAlpha = 0.25;
      ctx.fill();
      ctx.globalAlpha = 1.0;

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [state, isListening]);

  return (
    <div className="flex flex-col items-center justify-center p-2">
      <div className="relative w-[160px] h-[160px] flex items-center justify-center">
        <canvas ref={canvasRef} width={160} height={160} className="absolute inset-0" />
        <div className="z-10 text-center font-mono">
          <span className="text-[9px] tracking-widest uppercase text-slate-400 block">RAPHAEL STATE</span>
          <span className="text-xs font-bold tracking-wider font-display text-white uppercase drop-shadow-[0_0_8px_rgba(0,240,255,0.8)]">
            {isListening ? "LISTENING" : state}
          </span>
        </div>
      </div>
    </div>
  );
};
