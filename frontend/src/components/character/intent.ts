/**
 * Character Intent Model
 * ----------------------
 * The single source of truth for "what the character should be doing right
 * now". The character component reads this snapshot every frame and maps it
 * to springs/signals. UI code (and the WebSocket stream) only ever PUSH
 * intents — they never touch animation internals directly. This keeps the
 * trigger contract clean:
 *
 *   UI event / app state  ──push──▶  CharacterIntent  ──read──▶  motion
 */

import { RaphaelStateType } from "../../types";

/** Discrete facial expressions. */
export type Expression =
  | "neutral"
  | "happy"
  | "surprise"
  | "concern"
  | "thinking"
  | "speaking"
  | "sad"
  | "excited";

/** Mouth states. */
export type MouthMode =
  | "rest" // closed, neutral
  | "slight" // small open (concern/thinking)
  | "smile" // happy closed smile
  | "talk" // driven by TTS/audio amplitude
  | "oh"; // surprise "o" shape

/** Hand gesture presets. A gesture is a target pose for the two arms/hands. */
export type Gesture =
  | "rest" // arms relaxed at sides
  | "wave" // right hand raised, waving
  | "point" // right hand points (to UI / forward)
  | "confirm" // both hands do a small "ok/check" clasp
  | "thinking" // one hand near chin
  | "loading" // hands fidget / idle wait, gentle
  | "excited" // both hands up, open
  | "tap"; // one-hand quick tap feedback

/** Full-body motion modes (idle vs engaged vs transition). */
export type BodyMode =
  | "idle" // breathing + weight shift
  | "attentive" // slight forward lean, engaged
  | "speaking" // animated, expressive
  | "listening" // tilted head, receptive
  | "working" // focused, minimal motion
  | "celebrate"; // success bounce

export interface CharacterIntent {
  expression: Expression;
  mouth: MouthMode;
  gesture: Gesture;
  body: BodyMode;
  /** Normalized eye/head look target in [-1, 1]. 0,0 = center. */
  lookX: number;
  lookY: number;
  /** 0..1 how strongly the current expression should read (blend factor). */
  intensity: number;
  /** Live speech amplitude 0..1 to drive mouth "talk" openness. */
  talkLevel: number;
}

export const DEFAULT_INTENT: CharacterIntent = {
  expression: "neutral",
  mouth: "rest",
  gesture: "rest",
  body: "idle",
  lookX: 0,
  lookY: 0,
  intensity: 1,
  talkLevel: 0,
};

/**
 * Map the app's high-level runtime state onto a base character intent.
 * This is the default/ambient mapping; transient triggers (error, success,
 * click, hover) are layered on top by the context provider.
 */
export function intentFromAppState(state: RaphaelStateType): Partial<CharacterIntent> {
  switch (state) {
    case "listening":
      return { expression: "thinking", mouth: "slight", gesture: "listening" as any, body: "listening" };
    case "thinking":
      return { expression: "thinking", mouth: "slight", gesture: "thinking", body: "working" };
    case "executing":
      return { expression: "thinking", mouth: "slight", gesture: "loading", body: "working" };
    case "speaking":
      return { expression: "happy", mouth: "talk", gesture: "rest", body: "speaking" };
    case "error":
      return { expression: "concern", mouth: "slight", gesture: "rest", body: "attentive" };
    case "offline":
      return { expression: "sad", mouth: "rest", gesture: "rest", body: "idle" };
    case "idle":
    default:
      return { expression: "neutral", mouth: "rest", gesture: "rest", body: "idle" };
  }
}

/** One-shot trigger events the bus can fire (used for transient reactions). */
export type CharacterTrigger =
  | { kind: "error"; message?: string }
  | { kind: "success"; message?: string }
  | { kind: "click" }
  | { kind: "hover" }
  | { kind: "wave" }
  | { kind: "point" }
  | { kind: "celebrate" }
  | { kind: "surprise" };
