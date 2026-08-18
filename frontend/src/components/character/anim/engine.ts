/**
 * Raphael Character Animation Engine
 * ---------------------------------
 * A tiny, allocation-light animation core designed for 60fps character motion.
 *
 * Core ideas:
 *  - Animator: a single requestAnimationFrame loop. ALL character motion is
 *    driven from here and written DIRECTLY to DOM/SVG element transforms via
 *    refs (element.style.transform). React never re-renders per frame, so we
 *    keep a steady 60fps even on modest hardware.
 *  - Signal: a smoothed scalar value with a target. Two kinds:
 *      * SpringSignal  -> critically-ish damped spring (bouncy, lively follow-through)
 *      * EasedSignal   -> tween toward target with a named easing curve
 *  - Oscillator: a free-running sine/offset source used for idle breathing,
 *    swaying, and blink timers (continuous secondary motion).
 *
 * Everything is pure math + DOM writes. No React state, no GC churn in the loop.
 */

export type EasingFn = (t: number) => number;

export const Easing = {
  linear: (t: number) => t,
  // Smooth ease in/out (cubic) — used for posture transitions
  inOutCubic: (t: number) =>
    t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2,
  outCubic: (t: number) => 1 - Math.pow(1 - t, 3),
  inCubic: (t: number) => t * t * t,
  // Overshoot (back) — used for "pop" gestures (confirm, wave recoil)
  outBack: (t: number) => {
    const c1 = 1.70158;
    const c3 = c1 + 1;
    return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
  },
  outElastic: (t: number) => {
    const c4 = (2 * Math.PI) / 3;
    return t === 0 ? 0 : t === 1 ? 1 : Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * c4) + 1;
  },
  // Snappy, near-instant settle for micro feedback
  outQuad: (t: number) => 1 - (1 - t) * (1 - t),
  inOutSine: (t: number) => -(Math.cos(Math.PI * t) - 1) / 2,
};

/** Critically-damped-ish spring. Gives natural follow-through + settle. */
export class SpringSignal {
  value: number;
  target: number;
  velocity = 0;
  stiffness: number;
  damping: number;

  constructor(initial = 0, stiffness = 120, damping = 14) {
    this.value = initial;
    this.target = initial;
    this.stiffness = stiffness;
    this.damping = damping;
  }

  set(target: number) {
    this.target = target;
  }

  /** Hard reset (no motion) — used when we want to snap. */
  snap(value: number) {
    this.value = value;
    this.target = value;
    this.velocity = 0;
  }

  /** Advance by dt seconds. Returns the new value. */
  step(dt: number): number {
    // Clamp dt to avoid blowups after tab was backgrounded.
    const h = Math.min(dt, 0.05);
    const force = -this.stiffness * (this.value - this.target) - this.damping * this.velocity;
    this.velocity += force * h;
    this.value += this.velocity * h;
    return this.value;
  }

  get settled(): boolean {
    return Math.abs(this.value - this.target) < 0.001 && Math.abs(this.velocity) < 0.001;
  }
}

/** Tween toward a target using an easing curve over a fixed duration. */
export class EasedSignal {
  value: number;
  from: number;
  target: number;
  duration: number;
  elapsed = 0;
  easing: EasingFn;
  private _active = false;

  constructor(initial = 0, duration = 0.4, easing: EasingFn = Easing.inOutCubic) {
    this.value = initial;
    this.from = initial;
    this.target = initial;
    this.duration = duration;
    this.easing = easing;
  }

  set(target: number, duration = this.duration, easing: EasingFn = this.easing) {
    if (target === this.target) return;
    this.from = this.value;
    this.target = target;
    this.duration = Math.max(0.0001, duration);
    this.elapsed = 0;
    this.easing = easing;
    this._active = true;
  }

  step(dt: number): number {
    if (!this._active) return this.value;
    this.elapsed += dt;
    const t = Math.min(1, this.elapsed / this.duration);
    this.value = this.from + (this.target - this.from) * this.easing(t);
    if (t >= 1) this._active = false;
    return this.value;
  }

  get active(): boolean {
    return this._active;
  }
}

/** Continuous oscillator — breathing, sway, blink scheduling. */
export class Oscillator {
  phase = 0;
  freq: number; // Hz
  amplitude = 1;
  offset = 0;

  constructor(freq = 0.25, amplitude = 1, offset = 0) {
    this.freq = freq;
    this.amplitude = amplitude;
    this.offset = offset;
  }

  step(dt: number): number {
    this.phase += dt * this.freq * Math.PI * 2;
    return this.offset + Math.sin(this.phase) * this.amplitude;
  }
}

/** Stable, jittered interval generator for organic blink/idle timing. */
export class PulseTimer {
  private t = 0;
  interval: number;
  private jitter: number;
  private next: number;

  constructor(interval = 4, jitter = 2) {
    this.interval = interval;
    this.jitter = jitter;
    this.next = interval + (Math.random() - 0.5) * 2 * jitter;
  }

  /** Returns true exactly on the frame a pulse fires. */
  step(dt: number): boolean {
    this.t += dt;
    if (this.t >= this.next) {
      this.t = 0;
      this.next = this.interval + (Math.random() - 0.5) * 2 * this.jitter;
      return true;
    }
    return false;
  }
}

export type FrameCb = (dt: number, time: number) => void;

/**
 * The single rAF driver. Components register frame callbacks; the loop calls
 * them all in order each frame. Designed so one Animator serves the whole
 * character stage.
 */
export class Animator {
  private callbacks = new Set<FrameCb>();
  private raf = 0;
  private last = 0;
  private running = false;
  time = 0;

  add(cb: FrameCb): () => void {
    this.callbacks.add(cb);
    if (!this.running) this.start();
    return () => this.callbacks.delete(cb);
  }

  start() {
    if (this.running) return;
    this.running = true;
    this.last = performance.now();
    const tick = (now: number) => {
      if (!this.running) return;
      let dt = (now - this.last) / 1000;
      this.last = now;
      // Clamp huge gaps (tab switch) so springs don't explode.
      if (dt > 0.1) dt = 0.1;
      this.time += dt;
      this.callbacks.forEach((cb) => cb(dt, this.time));
      this.raf = requestAnimationFrame(tick);
    };
    this.raf = requestAnimationFrame(tick);
  }

  stop() {
    this.running = false;
    if (this.raf) cancelAnimationFrame(this.raf);
    this.raf = 0;
  }
}

/** Helpers to write GPU-friendly transforms. */
export function translate3d(x: number, y: number, z = 0): string {
  return `translate3d(${x.toFixed(2)}px, ${y.toFixed(2)}px, ${z.toFixed(1)}px)`;
}

export function rotateX(deg: number): string {
  return `rotateX(${deg.toFixed(2)}deg)`;
}
export function rotateY(deg: number): string {
  return `rotateY(${deg.toFixed(2)}deg)`;
}
export function rotateZ(deg: number): string {
  return `rotateZ(${deg.toFixed(2)}deg)`;
}
export function scale3d(s: number, sy = s, sz = 1): string {
  return `scale3d(${s.toFixed(4)}, ${sy.toFixed(4)}, ${sz.toFixed(1)})`;
}

/** Clamp helper. */
export const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));
/** Lerp helper. */
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
