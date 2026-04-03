# KORA

KORA is a continuity-first local/cloud hybrid AI system under active development.

## Repository hygiene

This repository stores source code and selected canon/config files only.
It must not store machine-local secrets, runtime memory, or generated session state.

### Never commit

- `.env`
- `memory/*.jsonl`
- `memory/confinement_state.json`
- logs, snapshots, temp files, exported transcripts, or generated audio
- API keys, tokens, passwords, private URLs, or local-only credentials

### Local-only runtime state

These belong on the machine running KORA, not in Git:

- `.env`
- `memory/facts.jsonl`
- `memory/signals.jsonl`
- `memory/confinement_state.json`
- any local bridge state, handoff dumps, or volatile ledger exports

### Operational note

If any secret was ever committed, assume it is burned and rotate it.
Removing a file from the current branch does not erase commit history.

## Suggested local bootstrap

Create a local `.env` file and any runtime memory files directly on the host.
Do not sync them back into this repository.
