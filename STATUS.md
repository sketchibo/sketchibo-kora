# KORA Local — Status & Repo Map
**Updated:** 2026-04-03
**Mode:** Phone-only survival (Pixel 6A, no VPS)
**Canonical repo root:** `~/kora_local`

---

## Deployment Truth

| Field | Value |
|---|---|
| Device | Pixel 6A |
| Repo | `~/kora_local` |
| Entry | `~/kora_local/kora.py` |
| Memory | `~/kora_local/memory/` |
| Identity | `~/kora_local/core/identity/` |
| Mode | KORA-Lite / survival config |
| VPS | Gone (Vultr Seattle decommissioned) |
| Moto E15 | Offload node (authorized_keys not yet set) |

---

## Canonical Files (active, do not move)

```
kora.py                  — main entry point
kora_interpreter.py      — action interpreter
kora_tools.py            — tool dispatch
kora_confinement.py      — K-SCP enforcement
kora_jobs.py             — job runner
kora_lce.py              — Life Compression Engine
kora_snapshot.py         — snapshot utility
kora_pulse.py            — heartbeat / selfcheck
kora_web.py              — web interface
kora_mcp.py              — MCP bridge
kora_probe.py            — diagnostic probe
kora_fact_append.py      — memory write
kora_context_dump.py     — context export
kora_video.py            — video pipeline
mail_bridge.py           — mail bridge
ask_venice.py            — Venice API
grow.py                  — growth proposals
config.json              — runtime config
.env                     — secrets (not committed)
boot_kora.sh             — boot script
start_kora.sh            — start script
```

### Core directories
```
core/identity/           — SOUL.md, IDENTITY.md, CHARTER.md, USER.md
core/empathy/            — empathy system
core/memory/             — memory index
core/profiles/           — persona, voice, memoic profiles
memory/                  — facts.jsonl, trajectory.json, startup_context.json,
                           guidance.md, person_model.json, rapport_state.json
crypto/                  — moonshot watcher, paper trading
server/                  — voice server
ui/                      — web UI
voice/                   — NeMo adapter
voices/                  — Piper voice models
piper/                   — Piper config
bin/                     — CLI entry points
growth/                  — growth proposal system
jobs/                    — job definitions
docs/                    — K-SCP, handoff docs, server queue
ledger.jsonl             — append-only chat/growth history
```

---

## Non-Canonical / Clutter (moving to _archive/)

```
kora.py.manualpatch.20260403_042650   — stale backup
kora.py.BAK.20260319_210058           — stale backup (already in git history)
kora.py.BAK.TONE.20260319_213230      — stale backup
kora.py.BROKEN.20260319_211616        — stale backup
kora.py.before_retry                  — stale backup
kora.py.broken                        — stale backup
kora.py.save / .save.1 / .save.2      — stale backups
kora_interpreter.py.badpaste_*        — stale backup
kora_web.py.BAK.*                     — stale backup
kora_pulse_patch.py                   — applied patch, stale
handoff/                              — old VPS handoff bundle
triage/                               — old debug dumps
path/                                 — paste mistake directory
"udo apt install -y tmux"             — typo directory
abc.txt / my_video.txt / real_video.txt / test.py / test_transcript.txt — scratch files
transfer_core.txt / kora_ask.sh / gemini_test.sh / wire_confinement_patch.py — stale
kora.py.save in handoff/              — stale copy
```

---

## Dead / Confusing Paths

| Path | Status |
|---|---|
| `~/kora/` | Dead stub — only has memory/ shadow copies |
| `.aider.*` | Aider cache (removed in prior cleanup per git log) |
| `.venv-piper/` `.venv-voice/` | Virtual envs — large, possibly unused |

---

## Health (current)

| System | Status |
|---|---|
| Python | ok |
| Repo found | ok |
| Memory files | ok |
| Ollama installed | yes — not running |
| Ollama models | unknown (not started) |
| Voice (piper) | unknown |
| API keys | check .env |
| VPS | gone |

---

## Trajectory

**Phase:** Phone-only survival
**Now:**
1. Clean repo clutter → _archive/
2. Stabilize kora.py (single source of truth)
3. Verify local Ollama path + pull one model

**Next:**
1. Restore distinct Kora voice
2. Tighten selfcheck to be evidence-based
3. Wire Moto E15 authorized_keys

**Later (parked):**
- VPS reconnect
- Cloud burst / council
- Video director branch
