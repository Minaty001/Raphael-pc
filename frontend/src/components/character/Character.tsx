/**
 * Character — procedural 2.5D anime schoolgirl.
 * --------------------------------------------
 * Fully vector (SVG), zero external assets. Built from depth-sorted named
 * layer groups so the animation engine can drive each part independently:
 *
 *   depth order (back -> front):
 *     gBackHair  : hair behind the body
 *     gArmL      : far arm (behind torso)
 *     gBody      : torso, skirt, legs, socks, shoes
 *     gArmR      : near arm
 *     gHead      : head + face (parallax-turns relative to body for 2.5D)
 *       gFace    : eyes, brows, blush, nose, mouth (expression-driven)
 *       gBangs   : front fringe (overlaps forehead)
 *       gClip    : hair accessory
 *
 * Motion is driven from a single rAF loop (see engine.ts) that reads the
 * merged CharacterIntent from CharacterContext and eases a set of springs
 * toward expression/gesture/body targets. Nothing re-renders React per frame.
 */

import React, { useEffect, useRef } from "react";
import {
  Animator,
  SpringSignal,
  Oscillator,
  PulseTimer,
  Easing,
  clamp,
} from "./anim/engine";
import { useCharacter } from "./CharacterContext";
import { CharacterIntent, DEFAULT_INTENT, Expression, Gesture, BodyMode } from "./intent";

// ---------------------------------------------------------------------------
// Expression -> continuous facial parameter targets
// ---------------------------------------------------------------------------
interface FaceParams {
  eyeOpen: number; // 0 closed .. 1 open
  eyeCurve: number; // 0 round .. 1 happy-arc (^_^)
  browAngle: number; // deg, + = inner-down (sad/concern)
  mouthOpen: number; // 0 .. 1
  mouthSmile: number; // -1 frown .. +1 smile
  blush: number; // 0 .. 1
}
const FACE: Record<Expression, FaceParams> = {
  neutral: { eyeOpen: 1, eyeCurve: 0, browAngle: 0, mouthOpen: 0.0, mouthSmile: 0.12, blush: 0 },
  happy: { eyeOpen: 0.95, eyeCurve: 0.45, browAngle: -3, mouthOpen: 0, mouthSmile: 0.9, blush: 0.18 },
  excited: { eyeOpen: 1, eyeCurve: 0.7, browAngle: -6, mouthOpen: 0.45, mouthSmile: 0.95, blush: 0.32 },
  surprise: { eyeOpen: 1, eyeCurve: 0, browAngle: 6, mouthOpen: 0.65, mouthSmile: -0.05, blush: 0.12 },
  concern: { eyeOpen: 0.8, eyeCurve: 0, browAngle: 9, mouthOpen: 0.03, mouthSmile: -0.5, blush: 0 },
  thinking: { eyeOpen: 0.85, eyeCurve: 0, browAngle: 4, mouthOpen: 0.02, mouthSmile: 0.0, blush: 0 },
  speaking: { eyeOpen: 0.95, eyeCurve: 0.3, browAngle: -2, mouthOpen: 0.18, mouthSmile: 0.85, blush: 0.1 },
  sad: { eyeOpen: 0.8, eyeCurve: 0, browAngle: 11, mouthOpen: 0.02, mouthSmile: -0.7, blush: 0.05 },
};

// ---------------------------------------------------------------------------
// Gesture -> arm pose targets. Each arm: shoulder (upper) + elbow (fore) angle.
// Pivots are defined in the SVG (see below). Angles in degrees.
// ---------------------------------------------------------------------------
interface ArmPose {
  lu: number;
  lf: number;
  ru: number;
  rf: number;
}
const ARMS: Record<Gesture, ArmPose> = {
  rest: { lu: 10, lf: 12, ru: -10, rf: -12 },
  wave: { lu: 12, lf: 18, ru: -150, rf: -25 },
  point: { lu: 10, lf: 14, ru: -78, rf: -8 },
  confirm: { lu: -42, lf: -60, ru: -42, rf: -60 },
  thinking: { lu: 8, lf: 14, ru: -55, rf: -120 },
  loading: { lu: 14, lf: 16, ru: -14, rf: -16 },
  excited: { lu: -150, lf: -22, ru: -150, rf: -22 },
  tap: { lu: 10, lf: 12, ru: -70, rf: -40 },
};

// Shoulder / elbow pivot coordinates in SVG user space.
const SHOULDER_L = { x: 138, y: 250 };
const SHOULDER_R = { x: 222, y: 250 };
const ELBOW_L = { x: 120, y: 330 };
const ELBOW_R = { x: 240, y: 330 };

// Body motion: weight shift (lean) + full-body yaw (parallax) targets.
const BODY: Record<BodyMode, { lean: number; yaw: number; breath: number }> = {
  idle: { lean: 0, yaw: 0, breath: 1 },
  attentive: { lean: 0.25, yaw: 0.15, breath: 0.8 },
  speaking: { lean: -0.15, yaw: -0.1, breath: 1.2 },
  listening: { lean: 0.1, yaw: 0.2, breath: 0.7 },
  working: { lean: 0.05, yaw: 0.05, breath: 0.6 },
  celebrate: { lean: -0.3, yaw: 0, breath: 1.5 },
};

export const Character: React.FC<{ className?: string }> = ({ className }) => {
  const char = useCharacter();

  // Refs to every animated SVG node.
  const gChar = useRef<SVGGElement>(null); // whole body (breath + lean + yaw)
  const gBackHair = useRef<SVGGElement>(null);
  const gArmL = useRef<SVGGElement>(null);
  const gArmLFore = useRef<SVGGElement>(null);
  const gArmR = useRef<SVGGElement>(null);
  const gArmRFore = useRef<SVGGElement>(null);
  const gHead = useRef<SVGGElement>(null);
  const gFace = useRef<SVGGElement>(null);
  const eyeL = useRef<SVGGElement>(null);
  const eyeR = useRef<SVGGElement>(null);
  const pupilL = useRef<SVGGElement>(null);
  const pupilR = useRef<SVGGElement>(null);
  const browL = useRef<SVGGElement>(null);
  const browR = useRef<SVGGElement>(null);
  const happyEyeL = useRef<SVGGElement>(null);
  const happyEyeR = useRef<SVGGElement>(null);
  const blushL = useRef<SVGEllipseElement>(null);
  const blushR = useRef<SVGEllipseElement>(null);
  const mouth = useRef<SVGPathElement>(null);
  const shadow = useRef<SVGEllipseElement>(null);

  useEffect(() => {
    const animator = new Animator();

    // --- Springs for every continuous parameter ---
    const mk = (v: number, s = 130, d = 14) => new SpringSignal(v, s, d);
    const s = {
      eyeOpen: mk(1),
      eyeCurve: mk(0),
      browAngle: mk(0),
      mouthOpen: mk(0),
      mouthSmile: mk(0.12),
      blush: mk(0),
      pupX: mk(0, 90, 12),
      pupY: mk(0, 90, 12),
      headYaw: mk(0, 110, 16),
      headPitch: mk(0, 110, 16),
      bodyLean: mk(0, 80, 14),
      bodyYaw: mk(0, 80, 14),
      breathAmp: mk(1, 60, 14),
      lu: mk(10),
      lf: mk(12),
      ru: mk(-10),
      rf: mk(-12),
      gesturePulse: mk(0, 200, 18),
    };

    // Continuous oscillators.
    const breath = new Oscillator(0.32, 1, 0); // ~3s breathing cycle
    const sway = new Oscillator(0.18, 1, 0); // gentle idle weight sway
    const waveOsc = new Oscillator(2.4, 1, 0); // waving speed
    const fidget = new Oscillator(1.1, 1, 0); // loading fidget
    const talkOsc = new Oscillator(7.5, 1, 0); // mouth flap when speaking
    const blinkTimer = new PulseTimer(4.2, 2.0);
    let blinkT = -1; // <0 = not blinking

    let lastGesture: Gesture = "rest";

    const frame = (dt: number, time: number) => {
      const intent: CharacterIntent = char.getIntent();

      // --- Expression targets ---
      const f = FACE[intent.expression] ?? FACE.neutral;
      s.eyeOpen.set(f.eyeOpen);
      s.eyeCurve.set(f.eyeCurve);
      s.browAngle.set(f.browAngle);
      s.mouthSmile.set(f.mouthSmile);
      s.blush.set(f.blush * intent.intensity);

      // --- Body targets ---
      const b = BODY[intent.body] ?? BODY.idle;
      s.bodyLean.set(b.lean + sway.step(dt) * 0.08);
      s.bodyYaw.set(b.yaw);
      s.breathAmp.set(b.breath);

      // --- Head look: eye-tracking + head turn (parallax) ---
      s.headYaw.set(intent.lookX * 0.8);
      s.headPitch.set(intent.lookY * 0.5);
      s.pupX.set(intent.lookX * 1.0);
      s.pupY.set(intent.lookY * 1.0);

      // --- Gesture targets (with special motion) ---
      const arm = ARMS[intent.gesture] ?? ARMS.rest;
      if (intent.gesture !== lastGesture) {
        lastGesture = intent.gesture;
        if (intent.gesture === "tap") s.gesturePulse.set(1);
      }
      s.lu.set(arm.lu);
      s.lf.set(arm.lf);
      s.ru.set(arm.ru);
      s.rf.set(arm.rf);
      if (s.gesturePulse.value > 0.01) s.gesturePulse.set(0); // decay

      // --- Mouth: talk overrides base open ---
      let mouthOpen = f.mouthOpen;
      const isTalking =
        intent.mouth === "talk" ||
        intent.expression === "speaking" ||
        intent.talkLevel > 0.02;
      if (isTalking) {
        const amp = intent.talkLevel > 0.02 ? intent.talkLevel : 0.55 + 0.45 * talkOsc.step(dt);
        mouthOpen = clamp(0.15 + amp * 0.6, 0.1, 0.95);
      }
      if (intent.mouth === "oh") mouthOpen = Math.max(mouthOpen, 0.65);
      s.mouthOpen.set(mouthOpen);

      // --- Blink scheduling ---
      if (blinkTimer.step(dt) && blinkT < 0) blinkT = 0;
      let blink = 0;
      if (blinkT >= 0) {
        blinkT += dt;
        if (blinkT < 0.07) blink = blinkT / 0.07;
        else if (blinkT < 0.16) blink = 1 - (blinkT - 0.07) / 0.09;
        else blinkT = -1;
      }
      const eyeOpenNow = s.eyeOpen.value * (1 - blink);

      // --- Step all springs ---
      s.eyeOpen.step(dt);
      s.eyeCurve.step(dt);
      s.browAngle.step(dt);
      s.mouthSmile.step(dt);
      s.blush.step(dt);
      s.pupX.step(dt);
      s.pupY.step(dt);
      s.headYaw.step(dt);
      s.headPitch.step(dt);
      s.bodyLean.step(dt);
      s.bodyYaw.step(dt);
      s.breathAmp.step(dt);
      s.lu.step(dt);
      s.lf.step(dt);
      s.ru.step(dt);
      s.rf.step(dt);
      s.gesturePulse.step(dt);
      s.mouthOpen.step(dt);

      // ====================================================================
      // WRITE TRANSFORMS (GPU-friendly; SVG transform attribute, pivoted).
      // ====================================================================
      const breathY = -2 - breath.step(dt) * 2.2 * s.breathAmp.value;
      const lean = s.bodyLean.value;
      const yaw = s.bodyYaw.value;
      if (gChar.current) {
        gChar.current.setAttribute(
          "transform",
          `translate(0 ${breathY.toFixed(2)}) rotate(${(lean * 3).toFixed(2)} 180 540) translate(${(yaw * 10).toFixed(2)} 0)`
        );
      }
      if (shadow.current) {
        const sc = 1 - breathY * 0.01;
        shadow.current.setAttribute("transform", `translate(180 532) scale(${(sc).toFixed(3)} ${(sc * 0.45).toFixed(3)})`);
        shadow.current.setAttribute("opacity", (0.32 * (1 - breathY * 0.01)).toFixed(3));
      }

      // Arms (nested rotate groups). Right arm gets wave/fidget modulation.
      let ru = s.ru.value;
      let rf = s.rf.value;
      if (intent.gesture === undefined || intent.gesture === "wave") {
        // wave handled below via explicit gesture flag
      }
      if (lastGesture === "wave") ru += Math.sin(waveOsc.phase) * 14;
      if (lastGesture === "loading") {
        ru += Math.sin(fidget.phase) * 4;
        rf += Math.cos(fidget.phase) * 4;
      }
      if (lastGesture === "tap") {
        const p = s.gesturePulse.value;
        rf += p * 30;
        ru += -p * 10;
      }
      if (gArmL.current)
        gArmL.current.setAttribute("transform", `rotate(${s.lu.value.toFixed(2)} ${SHOULDER_L.x} ${SHOULDER_L.y})`);
      if (gArmLFore.current)
        gArmLFore.current.setAttribute("transform", `rotate(${s.lf.value.toFixed(2)} ${ELBOW_L.x} ${ELBOW_L.y})`);
      if (gArmR.current)
        gArmR.current.setAttribute("transform", `rotate(${ru.toFixed(2)} ${SHOULDER_R.x} ${SHOULDER_R.y})`);
      if (gArmRFore.current)
        gArmRFore.current.setAttribute("transform", `rotate(${rf.toFixed(2)} ${ELBOW_R.x} ${ELBOW_R.y})`);

      // Head: pseudo-3D turn (horizontal squash + parallax shift).
      if (gHead.current) {
        const yawR = (s.headYaw.value * 26 * Math.PI) / 180;
        const sx = (0.82 + 0.18 * Math.cos(yawR)).toFixed(3);
        const px = (s.headYaw.value * 7).toFixed(2);
        const py = (s.headPitch.value * 5).toFixed(2);
        gHead.current.setAttribute(
          "transform",
          `translate(${px} ${py}) scale(${sx} 1)`
        );
      }

      // Eyes: vertical openness + happy-arc crossfade.
      const eo = clamp(eyeOpenNow, 0.04, 1);
      if (eyeL.current) eyeL.current.setAttribute("transform", `scale(1 ${eo.toFixed(3)})`);
      if (eyeR.current) eyeR.current.setAttribute("transform", `scale(1 ${eo.toFixed(3)})`);
      const happy = s.eyeCurve.value;
      if (happyEyeL.current) happyEyeL.current.setAttribute("opacity", happy.toFixed(3));
      if (happyEyeR.current) happyEyeR.current.setAttribute("opacity", happy.toFixed(3));
      if (eyeL.current) eyeL.current.setAttribute("opacity", (1 - happy * 0.9).toFixed(3));
      if (eyeR.current) eyeR.current.setAttribute("opacity", (1 - happy * 0.9).toFixed(3));

      // Pupils: eye-tracking shift (clamped within eye).
      const pdx = (s.pupX.value * 6).toFixed(2);
      const pdy = (s.pupY.value * 4).toFixed(2);
      if (pupilL.current) pupilL.current.setAttribute("transform", `translate(${pdx} ${pdy})`);
      if (pupilR.current) pupilR.current.setAttribute("transform", `translate(${pdx} ${pdy})`);

      // Brows: rotate for expression (inner-up vs inner-down).
      const ba = s.browAngle.value;
      if (browL.current) browL.current.setAttribute("transform", `rotate(${ba.toFixed(2)} 158 112)`);
      if (browR.current) browR.current.setAttribute("transform", `rotate(${(-ba).toFixed(2)} 202 112)`);

      // Blush.
      const bl = s.blush.value;
      if (blushL.current) blushL.current.setAttribute("opacity", bl.toFixed(3));
      if (blushR.current) blushR.current.setAttribute("opacity", bl.toFixed(3));

      // Mouth: recompute path from open + smile.
      if (mouth.current) {
        const open = s.mouthOpen.value;
        const smile = s.mouthSmile.value;
        if (open > 0.08) {
          // Open mouth: ellipse-ish path.
          const rx = 9;
          const ry = 3 + open * 9;
          const cy = 196;
          const cx = 180;
          const d = `M ${cx - rx} ${cy} a ${rx} ${ry.toFixed(1)} 0 1 0 ${(rx * 2).toFixed(1)} 0 a ${rx} ${ry.toFixed(1)} 0 1 0 ${(-rx * 2).toFixed(1)} 0 Z`;
          mouth.current.setAttribute("d", d);
          mouth.current.setAttribute("fill", "#5a2230");
          mouth.current.setAttribute("stroke", "none");
        } else {
          // Closed/smile/frown curve.
          const cx = 180;
          const cy = 196;
          const w = 11;
          // control point y offset: negative => smile, positive => frown
          const cpy = cy + 6 + smile * 9;
          const d = `M ${cx - w} ${cy} Q ${cx} ${cpy.toFixed(1)} ${cx + w} ${cy}`;
          mouth.current.setAttribute("d", d);
          mouth.current.setAttribute("fill", "none");
          mouth.current.setAttribute("stroke", "#7a3b46");
          mouth.current.setAttribute("stroke-width", "2.4");
          mouth.current.setAttribute("stroke-linecap", "round");
        }
      }
    };

    const unsub = animator.add(frame);
    return () => {
      unsub();
      animator.stop();
    };
  }, [char]);

  return (
    <svg
      className={className}
      viewBox="0 0 360 560"
      width="100%"
      height="100%"
      preserveAspectRatio="xMidYMax meet"
      style={{ overflow: "visible" }}
    >
      <defs>
        <linearGradient id="hairGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#7d8cf5" />
          <stop offset="100%" stopColor="#4f63d6" />
        </linearGradient>
        <linearGradient id="uniGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#27345f" />
          <stop offset="100%" stopColor="#1a2347" />
        </linearGradient>
        <linearGradient id="skinGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#ffe6d6" />
          <stop offset="100%" stopColor="#ffd2bd" />
        </linearGradient>
        <radialGradient id="cheek" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#ff8fa0" stopOpacity="0.8" />
          <stop offset="100%" stopColor="#ff8fa0" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* Contact shadow on the floor (grounds the 2.5D figure) */}
      <ellipse ref={shadow} cx="180" cy="532" rx="86" ry="20" fill="#000" opacity="0.32" />

      <g ref={gChar}>
        {/* ---- BACK HAIR (behind everything) ---- */}
        <g ref={gBackHair}>
          <path
            d="M180 96 C 110 96 86 150 88 220 C 89 290 104 360 120 410 C 128 430 150 432 156 412 C 150 360 146 300 150 250 C 152 200 160 160 180 150 C 200 160 208 200 210 250 C 214 300 210 360 204 412 C 210 432 232 430 240 410 C 256 360 271 290 272 220 C 274 150 250 96 180 96 Z"
            fill="url(#hairGrad)"
          />
        </g>

        {/* ---- FAR ARM (left, behind torso) ---- */}
        <g ref={gArmL}>
          <path d="M138 250 C 124 280 118 320 120 360 L 132 360 C 130 320 136 284 150 256 Z" fill="url(#skinGrad)" />
          <g ref={gArmLFore}>
            <path d="M120 330 C 110 365 108 400 112 424 L 126 422 C 124 398 126 366 138 340 Z" fill="url(#skinGrad)" />
            <ellipse cx="118" cy="426" rx="13" ry="11" fill="url(#skinGrad)" />
          </g>
        </g>

        {/* ---- BODY (torso + skirt + legs + socks + shoes) ---- */}
        <g>
          {/* Neck */}
          <rect x="168" y="196" width="24" height="26" rx="10" fill="url(#skinGrad)" />
          {/* Torso / sailor top */}
          <path d="M138 244 C 140 224 160 214 180 214 C 200 214 220 224 222 244 L 230 320 L 130 320 Z" fill="url(#uniGrad)" />
          {/* White shirt collar + chest */}
          <path d="M158 218 L 180 238 L 202 218 L 196 210 L 164 210 Z" fill="#f3f6ff" />
          {/* Sailor collar */}
          <path d="M150 222 L 180 250 L 210 222 L 214 236 L 180 262 L 146 236 Z" fill="#e9eeff" />
          {/* Ribbon (cyan accent ties into HUD theme) */}
          <path d="M180 244 L 168 262 L 174 256 L 180 266 L 186 256 L 192 262 Z" fill="#56d9ff" />
          <circle cx="180" cy="252" r="4.5" fill="#56d9ff" />
          {/* Skirt (pleated trapezoid) */}
          <path d="M128 318 L 232 318 L 252 392 L 108 392 Z" fill="url(#uniGrad)" />
          <g stroke="#3a4a82" strokeWidth="2" opacity="0.6">
            <line x1="140" y1="320" x2="128" y2="390" />
            <line x1="160" y1="320" x2="156" y2="392" />
            <line x1="180" y1="320" x2="180" y2="392" />
            <line x1="200" y1="320" x2="204" y2="392" />
            <line x1="220" y1="320" x2="232" y2="390" />
          </g>
          {/* Legs */}
          <rect x="138" y="388" width="20" height="92" rx="9" fill="url(#skinGrad)" />
          <rect x="202" y="388" width="20" height="92" rx="9" fill="url(#skinGrad)" />
          {/* Socks */}
          <rect x="137" y="452" width="22" height="34" rx="8" fill="#e8edff" />
          <rect x="201" y="452" width="22" height="34" rx="8" fill="#e8edff" />
          {/* Shoes */}
          <path d="M134 484 q 14 12 30 4 l 0 10 q -16 8 -32 -2 Z" fill="#20283f" />
          <path d="M196 484 q 16 12 32 2 l 0 10 q -16 8 -32 2 Z" fill="#20283f" />
        </g>

        {/* ---- NEAR ARM (right) ---- */}
        <g ref={gArmR}>
          <path d="M222 250 C 236 280 242 320 240 360 L 228 360 C 230 320 224 284 210 256 Z" fill="url(#skinGrad)" />
          <g ref={gArmRFore}>
            <path d="M240 330 C 250 365 252 400 248 424 L 234 422 C 236 398 234 366 222 340 Z" fill="url(#skinGrad)" />
            <ellipse cx="242" cy="426" rx="13" ry="11" fill="url(#skinGrad)" />
          </g>
        </g>

        {/* ---- HEAD (parallax-turns relative to body) ---- */}
        <g ref={gHead}>
          {/* Head base + ears */}
          <ellipse cx="180" cy="150" rx="58" ry="66" fill="url(#skinGrad)" />
          <ellipse cx="128" cy="150" rx="9" ry="15" fill="url(#skinGrad)" />
          <ellipse cx="232" cy="150" rx="9" ry="15" fill="url(#skinGrad)" />

          {/* FACE (expression-driven) */}
          <g ref={gFace}>
            {/* Happy closed eyes (^_^) — crossfaded in by eyeCurve */}
            <g ref={happyEyeL} opacity="0">
              <path d="M150 150 Q 160 140 170 150" stroke="#3a2b4d" strokeWidth="3.2" fill="none" strokeLinecap="round" />
            </g>
            <g ref={happyEyeR} opacity="0">
              <path d="M190 150 Q 200 140 210 150" stroke="#3a2b4d" strokeWidth="3.2" fill="none" strokeLinecap="round" />
            </g>

            {/* Open round eyes (scaled vertically by eyeOpen) */}
            <g ref={eyeL}>
              <g transform="translate(160 152)">
                <ellipse cx="0" cy="0" rx="13" ry="17" fill="#fff" />
                <circle cx="0" cy="0" r="11" fill="#3b6fd6" />
                <g ref={pupilL}>
                  <circle cx="0" cy="0" r="6" fill="#15203f" />
                  <circle cx="-3" cy="-4" r="2.6" fill="#fff" />
                </g>
                <path d="M-13 152 a 13 17 0 0 1 26 0" fill="none" />
                <path d="M-13 -4 Q 0 -19 13 -4" stroke="#3a2b4d" strokeWidth="3" fill="none" strokeLinecap="round" />
              </g>
            </g>
            <g ref={eyeR}>
              <g transform="translate(200 152)">
                <ellipse cx="0" cy="0" rx="13" ry="17" fill="#fff" />
                <circle cx="0" cy="0" r="11" fill="#3b6fd6" />
                <g ref={pupilR}>
                  <circle cx="0" cy="0" r="6" fill="#15203f" />
                  <circle cx="-3" cy="-4" r="2.6" fill="#fff" />
                </g>
                <path d="M-13 -4 Q 0 -19 13 -4" stroke="#3a2b4d" strokeWidth="3" fill="none" strokeLinecap="round" />
              </g>
            </g>

            {/* Brows */}
            <g ref={browL}>
              <path d="M150 122 Q 160 116 170 122" stroke="#4f63d6" strokeWidth="3.4" fill="none" strokeLinecap="round" />
            </g>
            <g ref={browR}>
              <path d="M190 122 Q 200 116 210 122" stroke="#4f63d6" strokeWidth="3.4" fill="none" strokeLinecap="round" />
            </g>

            {/* Blush */}
            <ellipse ref={blushL} cx="146" cy="172" rx="13" ry="9" fill="url(#cheek)" opacity="0" />
            <ellipse ref={blushR} cx="214" cy="172" rx="13" ry="9" fill="url(#cheek)" opacity="0" />

            {/* Nose */}
            <path d="M180 160 q 3 6 -1 9" stroke="#e0a98f" strokeWidth="2" fill="none" strokeLinecap="round" />

            {/* Mouth (path recomputed per frame) */}
            <path ref={mouth} d="M169 196 Q 180 205 191 196" fill="none" stroke="#7a3b46" strokeWidth="2.4" strokeLinecap="round" />
          </g>

          {/* FRONT BANGS (overlap forehead, in front of face edges) */}
          <g>
            <path
              d="M124 150 C 120 96 150 70 180 70 C 210 70 240 96 236 150 C 232 120 214 104 196 110 C 200 122 196 134 188 138 C 192 120 180 112 172 120 C 176 134 168 140 160 138 C 166 120 150 116 144 126 C 150 110 134 116 130 130 C 132 138 128 144 124 150 Z"
              fill="url(#hairGrad)"
            />
          </g>

          {/* Hair clip accessory (right side) */}
          <g>
            <rect x="216" y="128" width="20" height="9" rx="3" fill="#56d9ff" opacity="0.95" transform="rotate(18 226 132)" />
            <circle cx="226" cy="132" r="4" fill="#bdf3ff" />
          </g>
        </g>
      </g>
    </svg>
  );
};
