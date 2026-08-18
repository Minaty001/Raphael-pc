# 🗺️ Raphael v3 — Restructured Knowledge / Build Order (KO)

This document reorganizes the project around its **actual dependency structure** rather than the
flat module list the old README implied. Treat the subsystems below as **one loop**, not 15
independent features:

> **Perceive → Understand → Remember → Decide → Plan → Act → Verify → Learn → Remember again.**

The runtime keeps that loop alive; the task engine lets it multitask; memory gives it continuity;
perception gives it awareness; learning changes future behavior; and the JARVIS HUD gives the user
visibility into what is actually happening.

---

## 🧭 The Real Dependency Graph

The subsystems are **not independent peers**. The correct dependency order is:

```
                    RAPHAEL RUNTIME
                          │
                          ▼
                  EVENT + STATE LAYER
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
        PERCEPTION     MEMORY       EXTERNAL EVENTS
             │            │            │
             └────────────┼────────────┘
                          ▼
                    COGNITIVE STATE
                          │
                          ▼
                  INTENT / DECISION
                          │
                 ┌────────┴────────┐
                 ▼                 ▼
                ASK               ACT
                                   │
                              PLANNER
                                   │
                              TASK ENGINE
                                   │
                                TOOLS
                                   │
                              VERIFICATION
                                   │
                         ┌─────────┴─────────┐
                         ▼                   ▼
                       MEMORY             LEARNING
                                             │
                                         REFLECTION
                                             │
                                        ADAPTATION
```

---

## 🔗 Critical Dependencies (do not implement in arbitrary order)

1. **Runtime before intelligence** — Event Bus → State → Workers. Without this, background
   intelligence becomes unreliable.
2. **Voice before voice-agent behavior** — Audio → VAD → Wake Word → STT → Intent. You cannot
   meaningfully test *"Raphael, open Chrome"* until the audio pipeline is reliable.
3. **Memory before learning** — Memory → Experience → Evidence → Learning. Learning without
   persistent experience is just a collection of rules.
4. **Planner before autonomous tasks** — Intent → Goal → Plan → Task → Tool → Verification. The
   planner/task infrastructure must become a single execution loop.
5. **Perception before proactivity** — Perception + Memory + Goals + Time → Proactivity. Otherwise
   Raphael generates generic suggestions rather than context-aware ones.

---

## 🎓 Reorganized Curriculum (18 Levels)

1. **Level 0 — System Foundation**: project structure, runtime architecture, event architecture.
2. **Level 1 — Async Runtime & Multitasking**: async/await, task engine, scheduler, resource mgmt.
3. **Level 2 — Real-Time Communication**: REST, WebSocket, frontend/backend separation.
4. **Level 3 — Voice Foundation**: capture, resampling, VAD, wake word, post-wake capture, STT, TTS.
5. **Level 4 — Perception**: environment + screen perception, multimodal state.
6. **Level 5 — Memory Architecture**: working, episodic, semantic, procedural, user model, vector retrieval.
7. **Level 6 — Context & Attention**: build current context; select what matters.
8. **Level 7 — Intent & Decision**: classification, ambiguity, clarification.
9. **Level 8 — Planning**: goals → sub-goals → dependencies → actions → verification.
10. **Level 9 — Tools & Action**: registry, schemas, execution, verification.
11. **Level 10 — Verification**: act → observe → verify (not assume success).
12. **Level 11 — Agent Loop**: combine everything into the central perceive→…→learn loop.
13. **Level 12 — Learning**: experience → pattern → evidence → confidence → skill.
14. **Level 13 — Reflection / Metacognition**: structured evaluation, not hidden chain-of-thought.
15. **Level 14 — Goals & Open Loops**: long-term goals, subgoals, unfinished tasks.
16. **Level 15 — Routines & Proactive Intelligence**: routine detection, reminders, curiosity, topics.
17. **Level 16 — Always-Alive Cognitive Runtime**: combine voice + tasks + memory + perception + scheduler.
18. **Level 17 — UI / Human Interface**: backend state → WS event → frontend state → UI (never invent state).
19. **Level 18 — Security & Privacy**: auth, permissions, sandbox, audit, privacy.

---

## 🛠️ Phased Implementation Plan

| Phase | Focus | Est. (part-time) |
|---|---|---|
| 1 | Foundation (Python/async, EventBus, state, config, logging) | 2–3 days |
| 2 | Background Runtime (queue, worker pool, scheduler, priorities, retries, deps, checkpoints) | 3–4 days |
| 3 | WebSocket + UI State (heartbeat, reconnect, REST, auth, React state) | 2–3 days |
| 4 | Voice (mic, resample, VAD, KWS, buffering, STT, TTS, barge-in) — **largest early allocation** | 5–7 days |
| 5 | Memory (working, episodic, semantic, procedural, user model, embeddings, retrieval) | 5–7 days |
| 6 | Perception (active window, screen capture, OCR, vision, screen state) | 4–6 days |
| 7 | Agent Loop (intent, planning, task graph, tools, verification, replanning) | 5–7 days |
| 8 | Learning (feedback, pattern detection, skills, failure learning) | 4–5 days |
| 9 | Goals + Proactivity (open loops, routines, reminders, curiosity) | 4–5 days |
| 10 | Always-Alive Integration | 3–4 days |
| 11 | Security Hardening (auth, gates, sandbox, audit) | 3–4 days |
| 12 | UI & Developer Experience (truth-driven HUD) | 3–5 days |
| 13 | Testing & Optimization (runtime, voice, memory, agent, multitasking, platforms) | 5–7 days |
| | **Total** | **48–67 days** |

> Realistic engineering estimate for one person working part-time — not a promise that a coding
> model can generate it in one shot.

---

## ✅ Behavior Checkpoints (ask "does it work?", not "does the code exist?")

1. Can Raphael stay alive independently of the UI?
2. Can it run multiple background tasks without blocking interaction?
3. Can I say *"Raphael open Chrome"* naturally and have it work reliably?
4. Can Raphael remember something meaningful from a previous session?
5. Can Raphael understand what is currently on screen?
6. Can it execute a multi-step task and verify each step?
7. Can it learn a workflow from repeated behavior or explicit instruction?
8. Can it proactively help without becoming annoying?
9. Can it recover from a failed task?
10. Can all of this continue while the UI is closed?

---

## 🌳 Final Dependency Map

```
                 ┌───────────────┐
                 │  FOUNDATION   │  Python / Async
                 └───────┬───────┘
                         ▼
                 ┌───────────────┐
                 │ RUNTIME       │  Events / State
                 └───────┬───────┘
                         ▼
              ┌──────────┴──────────┐
              ▼                     ▼
          TASK SYSTEM             VOICE
              ▼                     ▼
              └──────────┬──────────┘
                         ▼
                    PERCEPTION
                         ▼
              ┌──────────┴──────────┐
              ▼                     ▼
           MEMORY                 CONTEXT
              └──────────┬──────────┘
                         ▼
                   INTENT / DECISION
                         ▼
                      PLANNER
                         ▼
                       TOOLS
                         ▼
                    VERIFICATION
                         ▼
                  MEMORY + LEARNING
                         ▼
                    REFLECTION
                         ▼
                GOALS + ROUTINES
                         ▼
                   PROACTIVITY
                         ▼
                ALWAYS-ALIVE BRAIN
                         ▼
                     JARVIS HUD
```

**The critical correction:** don't study/build Raphael as 15 independent features. Study it as one
loop. The runtime keeps the loop alive; the task engine multitasks; memory gives continuity;
perception gives awareness; learning changes the future; the HUD gives visibility.
