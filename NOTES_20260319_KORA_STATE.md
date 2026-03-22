# KORA state — 2026-03-19

## Working
- kora.py compiles
- fast mode responds again
- startup_brief exists
- empathy/profile files exist
- input classifier is wired into kora.py
- signals.jsonl is logging
- shell_blob classification works
- voice_identity classification works
- meta_system_talk classification works

## Not working / still weak
- council still times out
- voice_identity replies are still too generic / assistant-ish
- NeMo is only a scaffold, not live in the loop
- rapport_state.json is read but not learned/updated
- trajectory.json is read but not learned/updated
- shell/log text should be summarized/debugged, not treated like normal chat
- KORA still misreads messy voice-to-text / project nouns sometimes

## Important behavior notes
- Do not paste bash commands into KORA's You: prompt unless intentionally testing shell_blob mode
- Test one fast input at a time
- Multi-paste causes trajectory lock and muddies diagnosis

## Next build step
- Patch voice_identity mode so KORA answers in terms of tone/presence/rhythm, not generic support phrasing
- Leave council alone for now
- After that, move to the next list item: thin UI over fast mode
