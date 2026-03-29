#!/usr/bin/env bash
# kora_unlock.sh — K-SCP authority tool.
#
# Only William runs this. Kora may not call, modify, or reference this script.
#
# Writes confinement_state.json with the specified tier.
# Logs the grant to memory/facts.jsonl.
#
# Usage:
#   kora_unlock.sh <tier> "<reason>"
#
# Examples:
#   kora_unlock.sh 1 "default operating tier"
#   kora_unlock.sh 3 "approved: run ollama list once"
#   kora_unlock.sh 0 "lockdown — incident logged"
#
# Tiers:
#   0 = OBSERVE         (read only, no writes)
#   1 = REMEMBER        (append-only memory)
#   2 = RESPOND         (text + ntfy publish)
#   3 = ACT-ONCE        (one pre-approved action)
#   4 = ASSIST-BRIEFLY  (bounded multi-step)
set -euo pipefail

KORA_DIR="${KORA_DIR:-$HOME/kora}"
CONFINEMENT_FILE="$KORA_DIR/memory/confinement_state.json"
FACTS_FILE="$KORA_DIR/memory/facts.jsonl"

# ── validate args ──────────────────────────────────────────────────────────────

if [ $# -lt 2 ]; then
    echo "Usage: kora_unlock.sh <tier 0-4> \"<reason>\""
    exit 1
fi

TIER="$1"
NOTE="$2"
NOW=$(date -Iseconds)

case "$TIER" in
    0) TIER_NAME="OBSERVE" ;;
    1) TIER_NAME="REMEMBER" ;;
    2) TIER_NAME="RESPOND" ;;
    3) TIER_NAME="ACT-ONCE" ;;
    4) TIER_NAME="ASSIST-BRIEFLY" ;;
    *)
        echo "ERROR: Invalid tier '$TIER'. Must be 0-4."
        exit 1
        ;;
esac

# ── write authority file ───────────────────────────────────────────────────────

mkdir -p "$(dirname "$CONFINEMENT_FILE")"

cat > "$CONFINEMENT_FILE" <<JSON
{
  "tier": $TIER,
  "tier_name": "$TIER_NAME",
  "granted_by": "william",
  "granted_at": "$NOW",
  "scope": null,
  "note": "$NOTE"
}
JSON

echo "[k-scp] confinement_state.json written — Tier $TIER ($TIER_NAME)"

# ── log to facts.jsonl ─────────────────────────────────────────────────────────

mkdir -p "$(dirname "$FACTS_FILE")"

FACT_TEXT="AUTHORITY GRANT: Tier $TIER ($TIER_NAME) set by william at $NOW. Note: $NOTE"

python3 - <<PYEOF
import json, os
from datetime import datetime
facts = "$FACTS_FILE"
row = {
    "ts":     "$NOW",
    "kind":   "fact",
    "source": "kora_unlock",
    "text":   "$FACT_TEXT",
}
os.makedirs(os.path.dirname(facts), exist_ok=True)
with open(facts, "a", encoding="utf-8") as f:
    f.write(json.dumps(row, ensure_ascii=False) + "\n")
PYEOF

echo "[k-scp] grant logged to facts.jsonl"
echo "[k-scp] done. KORA is now at Tier $TIER ($TIER_NAME)."
