# KORA local-first Claude handoff

This file is a direct handoff artifact for KORA on the server.

## Core rule
KORA is the canonical local-first system.
Claude is an attached reasoning layer, not the source of truth.

## Required behavior
- KORA owns memory
- KORA owns ledger
- KORA owns continuity
- cloud reasoning may attach and detach
- continuity must survive cloud loss

## Immediate implementation target
Build the bridge so that:
1. KORA loads shared state at startup
2. external reasoning can write structured updates back
3. handoff state can be written before session/token loss
4. KORA resumes without reset

## State model
Two layers:

### Stable layer
- identity
- user model
- long-term goals
- principles
- canonical memory

### Evolving layer
- active goal
- recent decisions
- open loops
- continuity summary
- tone drift
- emerging traits
- active curiosities

## North star
Many minds may think through KORA.
Only KORA persists.

## Repo intent
This document exists so KORA can pull the brief directly from the repo if needed.
