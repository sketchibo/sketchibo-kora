# KORA

KORA is a local-first, continuity-oriented AI system designed to run on constrained devices (like phones) while optionally scaling to cloud compute.

## Core Principles
- Continuity over stateless responses
- Inspectable memory and behavior
- Local-first execution with optional cloud augmentation
- No silent actions or hidden mutations

## Quick Start
```bash
cd ~
git clone https://github.com/sketchibo/sketchibo-kora.git
cd sketchibo-kora
python3 kora.py
```

## Modes
- fast: lightweight responses (local-first)
- council: multi-perspective structured output
- think: deeper reasoning via larger models

## Structure (in progress cleanup)
- kora.py: main runtime loop
- kora_interpreter.py: intent parsing
- kora_tools.py: tool/action layer
- core/: identity, profiles, behavior logic
- memory/: persistent logs and state

## Status
Active development. Structure and modularization are being refined.
