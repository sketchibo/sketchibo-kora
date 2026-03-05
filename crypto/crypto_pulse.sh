#!/usr/bin/env bash
set -euo pipefail

PAIR_URL="https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd"
STATE_FILE="$HOME/kora/crypto/last.json"
LOG_FILE="$HOME/kora/crypto/pulse.log"
THRESHOLD="2.0"

mkdir -p "$(dirname "$STATE_FILE")"

RAW="$(curl -sS "$PAIR_URL")"
NOW="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

BTC="$(printf '%s' "$RAW" | jq -r '.bitcoin.usd // empty')"
ETH="$(printf '%s' "$RAW" | jq -r '.ethereum.usd // empty')"
SOL="$(printf '%s' "$RAW" | jq -r '.solana.usd // empty')"

if [ -z "$BTC" ] || [ -z "$ETH" ] || [ -z "$SOL" ]; then
  echo "[$NOW] price fetch failed: $RAW" | tee -a "$LOG_FILE"
  exit 1
fi

printf '{"ts":"%s","bitcoin":%s,"ethereum":%s,"solana":%s}\n' "$NOW" "$BTC" "$ETH" "$SOL" > "$HOME/kora/crypto/current.json"

if [ -f "$STATE_FILE" ]; then
  LAST_BTC="$(jq -r '.bitcoin' "$STATE_FILE")"
  LAST_ETH="$(jq -r '.ethereum' "$STATE_FILE")"
  LAST_SOL="$(jq -r '.solana' "$STATE_FILE")"

  pct() {
    python3 - <<PY
old = float("$1")
new = float("$2")
print(round(((new-old)/old)*100, 3) if old != 0 else 0.0)
PY
  }

  BTC_PCT="$(pct "$LAST_BTC" "$BTC")"
  ETH_PCT="$(pct "$LAST_ETH" "$ETH")"
  SOL_PCT="$(pct "$LAST_SOL" "$SOL")"

  echo "[$NOW] BTC=$BTC (${BTC_PCT}%) ETH=$ETH (${ETH_PCT}%) SOL=$SOL (${SOL_PCT}%)" | tee -a "$LOG_FILE"

  alert_if_big() {
    local name="$1"
    local pct="$2"
    python3 - <<PY
pct = float("$pct")
threshold = float("$THRESHOLD")
name = "$name"
if abs(pct) >= threshold:
    print(f"ALERT {name} moved {pct}%")
PY
  }

  alert_if_big BTC "$BTC_PCT" | tee -a "$LOG_FILE"
  alert_if_big ETH "$ETH_PCT" | tee -a "$LOG_FILE"
  alert_if_big SOL "$SOL_PCT" | tee -a "$LOG_FILE"
else
  echo "[$NOW] baseline set BTC=$BTC ETH=$ETH SOL=$SOL" | tee -a "$LOG_FILE"
fi

cp "$HOME/kora/crypto/current.json" "$STATE_FILE"
