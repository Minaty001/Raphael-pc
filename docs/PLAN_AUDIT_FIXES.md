# Audit Fix Plan — Wake Word Chain + 13 Bugs + UI Simplification

> Status: PLANNING (verified against source, not yet implemented).
> Verification method: every claim was read from actual source (file:line). No claim assumed.

## Audit claim verification (all CONFIRMED)
| # | Claim | Evidence |
|---|---|---|
| 1 | `sounddevice` only optional in requirements.txt | `requirements.txt:18-24` (optional comment block) |
| 2 | Porcupine absent → `TranscriptWakeProvider` (audio KWS dead for default) | `wakeword.py:215-224`, base `process_audio` returns False `wakeword.py:51-53` |
| 3 | Transcript wake path never wired (deadlock) | `process_transcript_segment` only in `wakeword.py:281` + tests; NOT called by `microphone.py`/`pipeline.py`/`always_alive.py` (grep: 6 matches, 0 in production path) |
| 3b | STT gated behind `COMMAND_LISTENING` only | `microphone.py:457` gate |
| 4 | Default `stt_provider="web"` can't decode native PCM | `stt.py:119-124` UTF-8 decode; `microphone.py:476` passes raw PCM |
| 5 | Default `tts_provider="web"` no audio w/o browser | `tts.py:45-64` waits, no playback; `pipeline.py:91` + `pipeline_helpers.py` call speak |
| 6 | `config.voice.wake_phrases` dead (hardcoded `DEFAULT_WAKE_WORDS` used) | `configuration.py:66-70` vs `wakeword.py:203` (`wake_words or DEFAULT_WAKE_WORDS`) |
| 7 | Frontend always self-speaks → double playback after #5 fix | `App.tsx:147-157` unconditional `speechSynthesis.speak` |
| 8 | "Voice: Ready" hardcoded | `TopBar.tsx:137` literal string |
| 9 | Voice failures silent (no health signal) | `always_alive.py:93` hardcodes voice="ready"; `health_monitor.py:89-96` only checks `wd.enabled` |
| 10 | Hardcoded default WS token | `configuration.py:177` `api_token="raphael_secret_token"` |
| 11 | `__pycache__` committed | repo has tracked `.pyc` (audit); no `.gitignore` confirmed |
| 12 | Fabricated context placeholder | `App.tsx:79-86` hardcoded; `.catch(()=>{})` line 104 |
| 13 | Unsupported browser silent no-op | `App.tsx:305-308` console.warn only |

## Decision points (locked)
- **Bug #2 → Option (A)**: fix the zero-cost transcript path. Keep Porcupine as optional upgrade (no `pvporcupine` dependency added). Do NOT add Picovoice key requirement.
- **Bug #5 → `tts_provider="edge"`**: `edge-tts` is ALREADY a hard dependency (`requirements.txt:14`), zero extra install.
- **Bug #4 → `stt_provider="vosk"`**: requires `vosk` (move to hard dep) + `VOSK_MODEL_PATH`. Refuse native mic when `stt_provider=="web"` with a clear log warning. Graceful fallback to `mock` if vosk unavailable.
- **Bug #3 fix**: remove the `COMMAND_LISTENING` gate in `microphone.py:457` so VAD segments + STT run in `WAKE_LISTENING` too; `_on_command_segment` → `pipeline.handle_speech_input` already does wake detection (passive-mode ignore). Delete dead `process_transcript_segment` + fix misleading docstring. VAD gating keeps it low-power (silence = no STT).
- **UI simplification**: KEEP the character/avatar system (user-added feature) — make it a Settings toggle (default OFF), do NOT delete. Sidebar 13→5, TopBar trim, dev pages → Settings tabs.

---

## PHASE A — Wake-word chain (#1–#5) + #6  [CRITICAL, do first]
1. `requirements.txt`: move `sounddevice`, `vosk` to hard deps; keep `pyttsx3` optional.
2. `configuration.py`: `stt_provider="vosk"`, `tts_provider="edge"`; pass `wake_phrases` into detector.
3. `wakeword.py:203`: use `config.voice.wake_phrases`; delete duplicate `DEFAULT_WAKE_WORDS`; remove dead `process_transcript_segment`; fix module docstring ("default" claim).
4. `microphone.py:457`: remove `COMMAND_LISTENING` gate → always VAD-segment + STT → `handle_speech_input`.
5. `microphone.py` + `always_alive.py`: when `stt_provider=="web"`, log clear warning "native mic capture requires vosk/whisper".
6. `always_alive.py:93`: set initial voice health to real mic availability (not hardcoded "ready").
7. **TEST** `tests/test_wake_e2e.py`: feed synthetic PCM through `MicrophoneSource._dispatch` with mocked STT returning "hey raphael what time is it"; assert `AudioState` → `COMMAND_LISTENING` and `handle_speech_input` invoked. (The missing regression test.)

## PHASE B — Backend bugs (#7 backend half, #9, #10, #11)
1. Backend: include active `tts_provider` name in `runtime.heartbeat` payload (`always_alive._emit_heartbeat`) so frontend can gate double-speak.
2. `#9`: publish real voice failures to health — mic probe fail → `health.update("voice","unavailable", reason)`; STT/VOSK missing → warn + health; TTS init fail → health.
3. `#10`: generate random `api_token` per-install on first run via `save_overrides()` (write `~/.raphael/config.override.json`); remove literal default.
4. `#11`: add `.gitignore` (`__pycache__/`, `*.pyc`, `node_modules/`, `dist/`, `.env`); `git rm --cached` tracked `.pyc`.

## PHASE C — Frontend voice truth (#7 frontend, #8, #12, #13)
1. `#7`: `App.tsx` self-speak only when active `tts_provider=="web"` (read from heartbeat/health).
2. `#8`: bind TopBar "Voice" pill to real health status (Ready/Unavailable + tooltip).
3. `#12`: `contextData` null initial + explicit loading/empty state in `ContextPanel`; stop swallowing fetch errors silently.
4. `#13`: disable/hide mic button with tooltip when Web Speech unsupported (no silent no-op).

## PHASE D — UI simplification (#1–#4)  [last, most subjective]
1. Sidebar 13→5 (Home, Chat, Memory, Planning[tabs: Goals/Routines/Reminders], Settings[advanced tabs]).
2. TopBar: brand + 1 status indicator + task counter (if>0) + settings icon; move gauges to RuntimePanel drawer; remove DEMO toggle + dev console from bar (into Settings).
3. Settings: absorb Models/Tools/System/Developer as tabs (Advanced collapsed).
4. Character: Settings toggle, default OFF; keep code (user feature) — minimal orb/ring fallback as default indicator.

---

## Hardware-unverifiable note
True E2E wake ("say Raphael" → mic → vosk → wake → command) needs a real mic + downloaded vosk model, which can't run in this environment. We verify via:
- The synthetic-PCM regression test (Phase A.7) proving the dispatch→wake→state path is WIRED (not dead).
- `py_compile` + full `pytest` suite green after each phase.
- A local runtime smoke run (start launcher, confirm "Microphone capture started", health reflects voice availability).

## Commit/push cadence
- One commit per phase (A→B→C→D), each pushed to `origin/main` after green tests + py_compile.
- Do NOT remove user-added features (character system) — only surface/trim them.
