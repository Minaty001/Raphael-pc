/**
 * CharacterStage — the 2.5D presentation surface.
 * -------------------------------------------------
 * Layers, back to front, for a pseudo-3D depth effect:
 *
 *   0. Sky / ambient gradient backdrop
 *   1. Far parallax band  (slow drift, blurred)        -> depth 3
 *   2. Mid parallax band  (medium drift)               -> depth 2
 *   3. Perspective floor grid (converges to a horizon) -> grounds the figure
 *   4. Character (with its own internal depth layers)  -> depth 1
 *   5. Foreground vignette + floating particles        -> depth 0 (closest)
 *
 * Depth technique:
 *   - Each band gets a different blur + brightness (atmospheric depth-of-field).
 *   - Parallax: pointer X/Y shifts each band by a fraction proportional to its
 *     depth (far moves least, near moves most). This sells the 3D volume.
 *   - The character's head independently performs a parallax yaw (see
 *     Character.tsx) so it reads as a separate depth plane in front of the body.
 *
 * Mouse / pointer drives BOTH the parallax AND the character's eye-tracking
 * (via setLook on the CharacterContext). On touch / no-pointer, it falls back
 * to gentle automatic sway.
 */

import React, { useEffect, useRef } from "react";
import { Character } from "./Character";
import { useCharacter } from "./CharacterContext";
import { SpringSignal, Animator } from "./anim/engine";

const DEPTH_FACTOR = [0.0, 6, 14, 24, 36]; // px max shift per layer index

export const CharacterStage: React.FC<{ className?: string; compact?: boolean }> = ({
  className,
  compact,
}) => {
  const char = useCharacter();
  const rootRef = useRef<HTMLDivElement>(null);
  const farRef = useRef<HTMLDivElement>(null);
  const midRef = useRef<HTMLDivElement>(null);
  const floorRef = useRef<HTMLDivElement>(null);
  const foreRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const animator = new Animator();
    const sx = new SpringSignal(0, 90, 13);
    const sy = new SpringSignal(0, 90, 13);
    const autoX = new SpringSignal(0, 40, 10);
    let t = 0;

    const onMove = (e: PointerEvent) => {
      const el = rootRef.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const nx = ((e.clientX - r.left) / r.width) * 2 - 1;
      const ny = ((e.clientY - r.top) / r.height) * 2 - 1;
      sx.set(clampn(nx));
      sy.set(clampn(ny));
      char.setLook(clampn(nx), clampn(ny));
    };
    const onLeave = () => {
      sx.set(0);
      sy.set(0);
      char.setLook(0, 0);
    };

    const root = rootRef.current;
    root?.addEventListener("pointermove", onMove);
    root?.addEventListener("pointerleave", onLeave);

    const frame = (dt: number) => {
      t += dt;
      sx.step(dt);
      sy.step(dt);
      // gentle auto-sway so it's alive even with no pointer
      autoX.set(Math.sin(t * 0.4) * 0.25);
      const ax = sx.value + autoX.value * (Math.abs(sx.value) < 0.05 ? 1 : 0);
      const ay = sy.value;
      const d = DEPTH_FACTOR;
      if (farRef.current) farRef.current.style.transform = `translate3d(${(ax * d[1]).toFixed(1)}px, ${(ay * d[1] * 0.5).toFixed(1)}px, 0)`;
      if (midRef.current) midRef.current.style.transform = `translate3d(${(ax * d[2]).toFixed(1)}px, ${(ay * d[2] * 0.5).toFixed(1)}px, 0)`;
      if (floorRef.current) floorRef.current.style.transform = `translate3d(${(ax * d[3]).toFixed(1)}px, 0, 0)`;
      if (foreRef.current) foreRef.current.style.transform = `translate3d(${(ax * d[4]).toFixed(1)}px, ${(ay * d[4] * 0.5).toFixed(1)}px, 0)`;
    };
    const unsub = animator.add(frame);
    return () => {
      unsub();
      animator.stop();
      root?.removeEventListener("pointermove", onMove);
      root?.removeEventListener("pointerleave", onLeave);
    };
  }, [char]);

  return (
    <div
      ref={rootRef}
      className={`character-stage relative overflow-hidden ${className ?? ""}`}
      style={{
        background:
          "radial-gradient(120% 90% at 50% 8%, rgba(86,217,255,0.10), transparent 55%), radial-gradient(80% 60% at 50% 100%, rgba(111,140,255,0.10), transparent 60%), #070b14",
        borderRadius: "18px",
        minHeight: compact ? 220 : 360,
        touchAction: "none",
      }}
    >
      {/* 1. Far parallax band */}
      <div
        ref={farRef}
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{ filter: "blur(7px)", opacity: 0.55 }}
      >
        <div className="absolute left-[8%] top-[18%] h-40 w-40 rounded-full bg-[#1b2a55] blur-2xl" />
        <div className="absolute right-[10%] top-[12%] h-32 w-32 rounded-full bg-[#16335f] blur-2xl" />
      </div>

      {/* 2. Mid parallax band */}
      <div
        ref={midRef}
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{ filter: "blur(3px)", opacity: 0.7 }}
      >
        <div className="absolute left-[16%] top-[30%] h-3 w-3 rounded-full bg-[#56d9ff]/70 shadow-[0_0_12px_#56d9ff]" />
        <div className="absolute right-[20%] top-[24%] h-2 w-2 rounded-full bg-[#6f8cff]/70 shadow-[0_0_10px_#6f8cff]" />
        <div className="absolute left-[28%] top-[44%] h-1.5 w-1.5 rounded-full bg-[#56d9ff]/50" />
        <div className="absolute right-[30%] top-[40%] h-1.5 w-1.5 rounded-full bg-[#6f8cff]/50" />
      </div>

      {/* 3. Perspective floor grid (converges to horizon) */}
      <div
        ref={floorRef}
        aria-hidden
        className="pointer-events-none absolute inset-x-0 bottom-0 h-[46%]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(86,217,255,0.18) 1px, transparent 1px), linear-gradient(90deg, rgba(86,217,255,0.14) 1px, transparent 1px)",
          backgroundSize: "40px 40px, 40px 40px",
          transform: "perspective(420px) rotateX(62deg)",
          transformOrigin: "bottom",
          maskImage: "linear-gradient(to top, #000 0%, transparent 92%)",
          WebkitMaskImage: "linear-gradient(to top, #000 0%, transparent 92%)",
          opacity: 0.6,
        }}
      />

      {/* 4. The character */}
      <div className="absolute inset-0 flex items-end justify-center pointer-events-none">
        <div className={compact ? "h-[230px] w-[180px]" : "h-[340px] w-[260px] sm:h-[400px] sm:w-[300px]"}>
          <Character className="h-full w-full" />
        </div>
      </div>

      {/* 5. Foreground vignette (closest plane) */}
      <div
        ref={foreRef}
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          boxShadow: "inset 0 0 90px 20px rgba(10,16,28,0.65)",
          borderRadius: "18px",
        }}
      />
    </div>
  );
};

function clampn(v: number) {
  return Math.max(-1, Math.min(1, v));
}
