/**
 * CharacterContext — the global trigger bus.
 * -------------------------------------------------
 * Any component (or the WebSocket layer in App.tsx) can call the exposed
 * helpers to make the character react: fireError(), fireSuccess(), tap(),
 * wave(), point(), celebrate(), surprise(). These are TRANSIENT one-shots
 * layered on top of the ambient intent derived from the app's runtime state.
 *
 * The provider keeps:
 *   - `state`: the app's RaphaelStateType (set by App each frame/event)
 *   - `base`: the ambient intent (from app state)
 *   - `transient`: a short-lived override produced by a trigger
 *
 * The character reads `getIntent()` which merges base + transient.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { RaphaelStateType } from "../../types";
import {
  CharacterIntent,
  CharacterTrigger,
  DEFAULT_INTENT,
  Expression,
  Gesture,
  MouthMode,
  BodyMode,
  intentFromAppState,
} from "./intent";

interface Transient {
  expires: number; // performance.now() ms
  intent: Partial<CharacterIntent>;
}

interface CharacterApi {
  setState: (s: RaphaelStateType) => void;
  setTalkLevel: (level: number) => void;
  fire: (t: CharacterTrigger) => void;
  fireError: (message?: string) => void;
  fireSuccess: (message?: string) => void;
  tap: () => void;
  wave: () => void;
  point: () => void;
  celebrate: () => void;
  surprise: () => void;
  /** Synchronous intent snapshot for the animation loop. */
  getIntent: () => CharacterIntent;
  /** Set eye/head look target [-1,1]. */
  setLook: (x: number, y: number) => void;
}

const Ctx = createContext<CharacterApi | null>(null);

// How long each transient trigger lives (ms).
const TTL: Record<string, number> = {
  error: 2600,
  success: 2200,
  click: 350,
  hover: 600,
  wave: 1800,
  point: 1400,
  celebrate: 2200,
  surprise: 1200,
};

function triggerIntent(t: CharacterTrigger): Partial<CharacterIntent> {
  switch (t.kind) {
    case "error":
      return { expression: "concern", mouth: "slight", gesture: "rest", body: "attentive" };
    case "success":
      return { expression: "excited", mouth: "smile", gesture: "excited", body: "celebrate" };
    case "click":
      return { gesture: "tap" as Gesture };
    case "hover":
      return { expression: "happy" as Expression, intensity: 0.6 };
    case "wave":
      return { expression: "happy", mouth: "smile", gesture: "wave", body: "speaking" };
    case "point":
      return { expression: "neutral", gesture: "point", body: "attentive" };
    case "celebrate":
      return { expression: "excited", mouth: "smile", gesture: "excited", body: "celebrate" };
    case "surprise":
      return { expression: "surprise", mouth: "oh", gesture: "excited", body: "attentive" };
  }
}

export const CharacterProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [appState, setAppState] = useState<RaphaelStateType>("idle");
  const talkRef = useRef(0);
  const lookRef = useRef({ x: 0, y: 0 });
  const transientRef = useRef<Transient | null>(null);
  const baseRef = useRef<Partial<CharacterIntent>>({});

  const setState = useCallback((s: RaphaelStateType) => setAppState(s), []);
  const setTalkLevel = useCallback((level: number) => (talkRef.current = level), []);
  const setLook = useCallback((x: number, y: number) => {
    lookRef.current.x = Math.max(-1, Math.min(1, x));
    lookRef.current.y = Math.max(-1, Math.min(1, y));
  }, []);

  const fire = useCallback((t: CharacterTrigger) => {
    transientRef.current = {
      expires: performance.now() + (TTL[t.kind] ?? 1000),
      intent: triggerIntent(t),
    };
  }, []);

  // Global delegated click/hover feedback: any interaction with a button-like
  // element makes the character do a small tap reaction. Non-invasive — no
  // per-component wiring required.
  useEffect(() => {
    const isInteractive = (el: Element | null): boolean => {
      if (!el) return false;
      const tag = el.tagName;
      return (
        tag === "BUTTON" ||
        tag === "A" ||
        (el as HTMLElement).role === "button" ||
        el.getAttribute("data-interactive") != null ||
        el.closest("button, a, [role='button'], [data-interactive]") != null
      );
    };
    const onClick = (e: Event) => {
      const tgt = e.target as Element;
      if (isInteractive(tgt)) fire({ kind: "click" });
    };
    document.addEventListener("pointerdown", onClick);
    return () => document.removeEventListener("pointerdown", onClick);
  }, [fire]);

  const api = useMemo<CharacterApi>(
    () => ({
      setState,
      setTalkLevel,
      fire,
      fireError: (m) => fire({ kind: "error", message: m }),
      fireSuccess: (m) => fire({ kind: "success", message: m }),
      tap: () => fire({ kind: "click" }),
      wave: () => fire({ kind: "wave" }),
      point: () => fire({ kind: "point" }),
      celebrate: () => fire({ kind: "celebrate" }),
      surprise: () => fire({ kind: "surprise" }),
      setLook,
      getIntent: () => {
        const now = performance.now();
        const tr = transientRef.current;
        if (tr && now > tr.expires) {
          transientRef.current = null;
        }
        const active = tr && now <= tr.expires ? tr.intent : {};
        const base = intentFromAppState(appState);
        baseRef.current = base;
        // Transient overrides base; talk level always reflects live speech.
        const merged: CharacterIntent = {
          ...DEFAULT_INTENT,
          ...base,
          ...active,
          talkLevel: talkRef.current,
          lookX: lookRef.current.x,
          lookY: lookRef.current.y,
        };
        return merged;
      },
    }),
    [appState, setState, setTalkLevel, fire, setLook]
  );

  return <Ctx.Provider value={api}>{children}</Ctx.Provider>;
};

export function useCharacter(): CharacterApi {
  const ctx = useContext(Ctx);
  if (!ctx) {
    // Safe no-op fallback so the app never crashes if used outside provider.
    return {
      setState: () => {},
      setTalkLevel: () => {},
      fire: () => {},
      fireError: () => {},
      fireSuccess: () => {},
      tap: () => {},
      wave: () => {},
      point: () => {},
      celebrate: () => {},
      surprise: () => {},
      setLook: () => {},
      getIntent: () => DEFAULT_INTENT,
    };
  }
  return ctx;
}
