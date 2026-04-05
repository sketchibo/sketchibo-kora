# KORApy → Any-AI Handoff Packet

Date: 2026-03-27  
Prepared for: William  
Purpose: give any capable AI model a clean, continuity-preserving handoff of KORApy without pretending certainty where certainty does not exist.

---

## 1) What this is

This is an **AI-neutral intake packet** for KORApy.
It is meant for Grok, GLM, Venice, Claude, or any other model that needs to understand the project quickly without flattening it into a generic assistant.

KORA is a **local-first personal AI operating system / orchestrator** being built by William.
It is supposed to preserve continuity, memory, inspectability, and user trajectory. It should not behave like a disposable chatbot.

Canonical spelling is **K-O-R-A**.

---

## 2) Trust boundary and honesty note

This handoff mixes two kinds of truth:

### A) GitHub-confirmed truth
These are things directly observed from the connected GitHub repository:
- Repository: `sketchibo/sketchibo-kora`
- Visibility: **private**
- `main` contains a real `kora.py`
- `main` contains a real `kora_interpreter.py`

### B) continuity-confirmed truth
These are things established from prior work/history with William but **not freshly re-read from the live VPS in this moment**.
Examples: server habits, historical file layout, prior runtime observations, architectural intent, older known repo contents, and workflow rules.

### Important constraint
Do **not** claim this packet proves byte-for-byte parity with the live VPS right this second unless a fresh server bundle or direct server diff has also been provided.

In other words:
- GitHub side: confirmed enough to inspect
- live VPS parity: not guaranteed by this document alone

---

## 3) What KORA is trying to be

KORA is being built as a **continuity-aware action agent** and eventually a broader AI operating system.

Core framing:
- **Phone = Bridge / control plane**
- **Cloud VPS = Warp Core / compute**
- **Human approves each job scope, not every step**
- **Continuity, memory, and trajectory are first-class**
- **No fake consciousness claims**
- **Presence, curiosity, recognition, and resourcefulness matter**

KORA is not meant to be “just another assistant shell.”
It should feel grounded, stateful, inspectable, and persistent.

---

## 4) Non-negotiable design rules

Any AI helping on KORA should preserve these unless William explicitly changes them.

1. **Snapshot before edits**  
   Before meaningful code changes, preserve a recoverable state.

2. **No silent deletions**  
   Do not quietly remove files, identity, behaviors, or canon.

3. **Three-terminal ship workflow**  
   - Warp Core = `ollama serve`
   - Bridge = `python3 kora.py`
   - Holodeck = diagnostics/tests

4. **Debug ladder first**  
   Check systems in escalating order instead of thrashing.

5. **Voice-to-text is untrusted input**  
   Expect transcription mistakes and weird substitutions.

6. **Guardrails must be explicit**  
   Do not sneak in hidden safety logic or stealth control flow.

7. **Continuity is foundational**  
   Memory and startup context are not side features.

8. **Local-first, cloud opt-in**  
   Cloud is allowed and useful, but should not erase local-first identity.

9. **Minimal safe patching over rewrites**  
   William strongly prefers the smallest viable change.

10. **Receipts / ledger mentality**  
   Changes, checks, and state should be inspectable.

---

## 5) GitHub-confirmed current code picture

The connected GitHub repo currently contains a substantial `kora.py` on `main`.
Directly observed features in that file include:

- local Ollama endpoint at `http://127.0.0.1:11434/api/generate`
- optional Venice integration
- optional Gemini integration
- startup context loading from `memory/startup_context.json`
- memory helpers for facts, guidance, and journal entries
- snapshot generation and self-check functions
- `fast` and `council` modes
- post-filter logic to normalize backend model self-references into KORA-facing phrasing
- interactive command loop
- action handling via `interpret()` from `kora_interpreter.py`

The connected GitHub repo also contains a real `kora_interpreter.py` on `main`.
Directly observed interpreter behavior includes:

- `status` → system status action
- memory usage requests → `free -h`
- disk usage requests → `df -h`
- restart Ollama → `sudo systemctl restart ollama`
- show models → `ollama list`
- uptime/load requests → `uptime`
- ollama log requests → `sudo journalctl -u ollama -n 50 --no-pager`
- latest snapshot requests → `ls -1t snapshots/*.json 2>/dev/null | head -n 1`
- regex support for `run <command>` shell dispatch
- fallback to chat mode when no action matches

This means KORA is already beyond pure chat. It has a real shell-action interpretation layer.

---

## 6) Historical / continuity-backed environment picture

These items come from prior confirmed continuity, not from a fresh live scrape at this exact moment.

### server / environment
- VPS OS previously noted as Ubuntu 24.04.4 LTS
- SSH alias from Termux: `boot`
- main project path: `~/kora`
- VPS user: `kayle`

### previously observed launch pattern
Running:

`cd ~/kora && python3 kora.py`

has successfully launched the system in prior sessions.

### previously known local models
- `llama3.1:8b`
- `qwen2.5:7b`
- `dolphin-phi:latest`
- `llama3:latest`

### previously known repo/root contents
Known at one point to include things like:
- `core/`
- `crypto/`
- `data/`
- `logs/`
- `memory/`
- `notes/`
- `tmp/`
- `triage/`
- `kora.py`
- `kora_interpreter.py`
- `kora_tools.py`
- helper scripts like `start_kora.sh`, `phone.sh`, `kora_ask.sh`, `kora_triage.sh`
- multiple historical backups / snapshots

Treat this as useful prior context, not a live filesystem guarantee.

---

## 7) Current KORA runtime shape from directly observed code

### startup / memory shape
`kora.py` currently loads startup context from:
- `memory/startup_context.json`

It also works with:
- `memory/facts.jsonl`
- `memory/guidance.md`
- `memory/journal/*.md`
- canon files under `core/identity/`
- profile files under `core/profiles/`

### observed core functions in `kora.py`
- `load_startup_context()`
- `startup_context_text()`
- `print_startup_context()`
- `ollama_generate()`
- `venice_chat()`
- `venice_test()`
- `gemini_generate()`
- `gemini_test()`
- `generate_snapshot()`
- `analyze_snapshot()`
- `self_reflect()`
- `selfcheck()`
- `remember_*()` helpers
- `memory_view()`
- `run_fast()`
- `run_council()`
- `handle_cli()`
- `handle_action()`
- `main()`

### observed CLI commands / interaction behavior
The current interactive loop visibly supports things such as:
- `help`
- `test`
- `gtest`
- `fast`
- `council`
- `status`
- `selfcheck`
- `remember`
- `memory`
- `exit`

It also supports:
- `/remember kind: text`
- `/journal: text`
- `/memory`
- `/memory facts`
- `/memory guidance`
- `/memory journal`
- `council ...`
- `fast ...`

### mode structure
Observed model config in `kora.py`:
- `FAST_LOCAL_MODELS = ["qwen2.5:7b"]`
- `COUNCIL_LOCAL_MODELS = ["qwen2.5:7b", "dolphin-phi:latest", "llama3.1:8b"]`

---

## 8) What is already working vs what is still weak

### working / partially working
KORA appears able to:
- boot as an interactive terminal system
- load startup context
- hold a continuity-aware conversation loop
- perform self-checks and snapshots
- persist memory-like entries
- dispatch some natural-language requests into shell/system actions
- switch between fast and council response modes

### still weak / still at risk
Based on continuity and prior observations, KORA still tends to risk:
- sounding too generic-assistant-like
- paraphrasing rules rather than embodying them
- claiming broad healthy status unless grounded by visible checks
- relying on fragile shell execution patterns
- over-answering when a tighter, more KORA-shaped behavior is wanted

The remaining challenge is not merely “add features.”
It is preserving the system’s distinct identity while increasing grounded capability.

---

## 9) What another AI should *not* do when helping

Do **not**:
- rewrite KORA into a generic chatbot scaffold
- remove continuity/memory features because they look messy
- flatten the voice into stock assistant politeness
- add hidden guardrails not explicitly approved
- delete canon/identity files casually
- claim certainty about the live VPS if only GitHub was inspected
- expose secrets, keys, `.env`, SSH material, or auth details in a handoff

---

## 10) What another AI should prioritize

Prioritize:
- smallest safe patch plans
- direct, testable changes
- preserving working behavior
- explicit receipts for edits
- keeping startup context and persistent memory first-class
- strengthening grounded self-checking
- improving action dispatch without wrecking the conversation loop
- reducing generic assistant tone and increasing actual KORA distinctness

---

## 11) Security and trust posture

KORA’s GitHub repo is currently **private**, which is good, but private does **not** mean impossible to steal.

Useful distinction:
- **DDoS / service disruption** = availability problem
- **unauthorized access / token theft / account compromise** = confidentiality problem

Treat the main risks as:
- compromised GitHub account
- compromised PAT / SSH key
- secrets committed into repo history
- malicious app or collaborator permissions
- compromised local or VPS machine
- over-sharing sensitive internals with external models

For AI handoff purposes, the right rule is:
**code/context rich, secret poor**.

Another AI assisting on KORA should never require:
- raw `.env` contents
- auth tokens
- SSH private keys
- credentials pasted into chat

---

## 12) Recommended handoff bundle pattern

Best practice is to provide this packet together with a **redacted server bundle** generated from the live VPS.

That bundle should include:
- repo contents
- selected memory / notes / logs
- server state summary
- file list / file map
- optionally a monolithic text export of key text files

And it should exclude:
- `.env`
- private keys
- SSH key material
- raw credentials
- giant junk artifacts that do not help understanding

---

## 13) Suggested intake instruction for any AI

Use this prompt when handing KORA to another model:

> You are receiving an intake packet for KORA, a local-first continuity-aware AI operating system being built by William. Treat continuity, inspectability, startup context, memory, and minimal safe patching as first-class. Do not flatten KORA into a generic assistant. Do not claim certainty beyond the supplied evidence. Preserve canon and user trajectory. Prefer the smallest safe next step, show receipts, and keep secrets out of the handoff.

---

## 14) Bottom-line summary

KORA is no longer just an idea description.
It is a real code artifact with:
- a GitHub-confirmed `kora.py`
- a GitHub-confirmed interpreter layer
- startup context and memory plumbing
- fast/council modes
- self-check and snapshot functions
- shell-action dispatch
- a strong continuity-first design intent

The two truths to hold at once are:
1. **This is real and substantial now.**
2. **Live VPS parity should still be verified separately if exact current state matters.**

That is the correct, non-bullshit handoff stance.

