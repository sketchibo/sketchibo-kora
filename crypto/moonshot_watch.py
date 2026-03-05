#!/usr/bin/env python3
import json
import math
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone

BASE = os.path.expanduser("~/kora/crypto")
os.makedirs(BASE, exist_ok=True)

STATE_FILE = os.path.join(BASE, "moonshot_state.json")
LOG_FILE = os.path.join(BASE, "moonshot_alerts.log")
SNAP_FILE = os.path.join(BASE, "moonshot_latest.json")

DEX = "https://api.dexscreener.com"
BIZ = "https://a.4cdn.org/biz/catalog.json"

# Hard bias toward meme/new stuff
MEME_WORDS = {
    "meme", "dog", "cat", "pepe", "frog", "inu", "elon", "trump",
    "moon", "pump", "chad", "wojak", "bonk", "degen", "ape", "gigachad"
}

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def fetch_json(url, timeout=20):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "KORA-Moonshot/1.0"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def safe_float(v, default=0.0):
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default

def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def log(msg):
    line = f"[{now_iso()}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def read_x_hits():
    """
    Optional future extension:
    Put a JSON file at ~/kora/crypto/x_hits.json like:
    {"DOGE": 12, "PEPE": 30}
    If absent, X contribution = 0.
    """
    path = os.path.join(BASE, "x_hits.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {str(k).upper(): int(v) for k, v in data.items()}
    except Exception:
        return {}

def biz_mentions():
    """
    Count rough ticker mentions from /biz/ catalog.
    We keep this light and noisy-on-purpose.
    """
    counts = {}
    try:
        pages = fetch_json(BIZ, timeout=20)
        for page in pages:
            for thread in page.get("threads", []):
                text = " ".join([
                    str(thread.get("sub", "")),
                    str(thread.get("com", "")),
                    str(thread.get("semantic_url", "")),
                ]).upper()
                # $TICKER style
                for m in re.findall(r"\$([A-Z]{2,10})", text):
                    counts[m] = counts.get(m, 0) + 1
                # plain uppercase words can be noisy, so keep stricter
                for m in re.findall(r"\b([A-Z]{3,6})\b", text):
                    if m not in {"AND", "THE", "FOR", "ARE", "NOT", "USD"}:
                        counts[m] = counts.get(m, 0) + 1
    except Exception as e:
        log(f"biz fetch failed: {e}")
    return counts

def is_memeish(text):
    t = (text or "").lower()
    return any(w in t for w in MEME_WORDS)

def latest_profiles():
    try:
        data = fetch_json(f"{DEX}/token-profiles/latest/v1", timeout=20)
        if isinstance(data, list):
            return data
        return data if isinstance(data, list) else []
    except Exception as e:
        log(f"profiles fetch failed: {e}")
        return []

def boosted_tokens():
    merged = []
    for path in ("/token-boosts/latest/v1", "/token-boosts/top/v1"):
        try:
            data = fetch_json(f"{DEX}{path}", timeout=20)
            if isinstance(data, list):
                merged.extend(data)
        except Exception as e:
            log(f"boost fetch failed ({path}): {e}")
    return merged

def token_pairs(chain_id, token_address):
    try:
        data = fetch_json(f"{DEX}/token-pairs/v1/{chain_id}/{token_address}", timeout=20)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []

def best_pair(pairs):
    if not pairs:
        return {}
    return max(
        pairs,
        key=lambda p: safe_float((p.get("liquidity") or {}).get("usd"), 0.0)
    )

def pct(old, new):
    if old in (None, 0):
        return 0.0
    try:
        return ((new - old) / old) * 100.0
    except Exception:
        return 0.0

def main():
    ts = now_iso()
    old_state = load_state()
    biz = biz_mentions()
    x_hits = read_x_hits()

    profiles = latest_profiles()
    boosts = boosted_tokens()

    candidates = {}

    # Seed from latest profiles (new stuff)
    for item in profiles:
        chain = item.get("chainId")
        addr = item.get("tokenAddress")
        if not chain or not addr:
            continue
        key = f"{chain}:{addr}"
        candidates[key] = {
            "chainId": chain,
            "tokenAddress": addr,
            "symbol": "",
            "name": "",
            "description": item.get("description", "") or "",
            "profile_url": item.get("url", "") or "",
            "boost_amount": 0.0,
            "profile_seen": True,
        }

    # Merge boosted/promoted tokens
    for item in boosts:
        chain = item.get("chainId")
        addr = item.get("tokenAddress")
        if not chain or not addr:
            continue
        key = f"{chain}:{addr}"
        row = candidates.setdefault(key, {
            "chainId": chain,
            "tokenAddress": addr,
            "symbol": "",
            "name": "",
            "description": item.get("description", "") or "",
            "profile_url": item.get("url", "") or "",
            "boost_amount": 0.0,
            "profile_seen": False,
        })
        row["boost_amount"] = max(row.get("boost_amount", 0.0), safe_float(item.get("amount"), 0.0))
        row["total_boost"] = max(safe_float(row.get("total_boost"), 0.0), safe_float(item.get("totalAmount"), 0.0))
        if item.get("description") and not row.get("description"):
            row["description"] = item.get("description")
        if item.get("url") and not row.get("profile_url"):
            row["profile_url"] = item.get("url")

    scored = []

    # Limit pair lookups to top 20 most interesting seeds to stay lightweight
    seeds = sorted(
        candidates.values(),
        key=lambda r: (r.get("profile_seen", False), r.get("boost_amount", 0.0), r.get("total_boost", 0.0)),
        reverse=True
    )[:20]

    for row in seeds:
        chain = row["chainId"]
        addr = row["tokenAddress"]

        pairs = token_pairs(chain, addr)
        pair = best_pair(pairs)

        base = pair.get("baseToken") or {}
        row["symbol"] = (base.get("symbol") or row.get("symbol") or "").upper()
        row["name"] = base.get("name") or row.get("name") or ""

        symbol = row["symbol"]
        name = row["name"]
        desc = row.get("description", "")

        liquidity = safe_float((pair.get("liquidity") or {}).get("usd"), 0.0)
        volume24 = safe_float((pair.get("volume") or {}).get("h24"), 0.0)
        price_change_5m = safe_float((pair.get("priceChange") or {}).get("m5"), 0.0)
        price_change_1h = safe_float((pair.get("priceChange") or {}).get("h1"), 0.0)
        buys_1h = safe_float(((pair.get("txns") or {}).get("h1") or {}).get("buys"), 0.0)
        sells_1h = safe_float(((pair.get("txns") or {}).get("h1") or {}).get("sells"), 0.0)
        pair_created_ms = pair.get("pairCreatedAt")

        age_hours = 9999.0
        if pair_created_ms:
            try:
                age_hours = max(0.0, (time.time() - (float(pair_created_ms) / 1000.0)) / 3600.0)
            except Exception:
                pass

        prior = old_state.get(f"{chain}:{addr}", {})
        prev_vol = safe_float(prior.get("volume24"), 0.0)
        prev_biz = safe_float(prior.get("biz_mentions"), 0.0)
        prev_x = safe_float(prior.get("x_mentions"), 0.0)

        biz_count = biz.get(symbol, 0) if symbol else 0
        x_count = x_hits.get(symbol, 0) if symbol else 0

        vol_accel = pct(prev_vol, volume24)
        biz_accel = pct(prev_biz if prev_biz else 1, biz_count if biz_count else 1)
        x_accel = pct(prev_x if prev_x else 1, x_count if x_count else 1)

        # Scoring: heavy bias toward fresh + meme + social ignition
        novelty_score = 0.0
        if row.get("profile_seen"):
            novelty_score += 18.0
        if age_hours <= 24:
            novelty_score += 12.0
        elif age_hours <= 72:
            novelty_score += 6.0

        meme_score = 0.0
        meme_blob = " ".join([symbol, name, desc, row.get("profile_url", "")])
        if is_memeish(meme_blob):
            meme_score += 18.0
        if symbol and symbol in {"PEPE", "BONK", "DOGE", "SHIB", "FLOKI", "TRUMP"}:
            meme_score += 12.0

        social_score = min(20.0, biz_count * 2.0)
        social_score += min(20.0, x_count * 1.5)
        if biz_count > 0 and x_count > 0:
            social_score += 8.0
        if biz_accel > 100:
            social_score += 5.0
        if x_accel > 100:
            social_score += 5.0

        market_score = 0.0
        market_score += min(20.0, max(0.0, price_change_5m) * 2.0)
        market_score += min(12.0, max(0.0, price_change_1h) * 0.8)
        if vol_accel > 50:
            market_score += 6.0
        if buys_1h > sells_1h:
            market_score += 4.0

        boost_score = min(20.0, safe_float(row.get("total_boost", 0.0)) * 0.25 + safe_float(row.get("boost_amount", 0.0)) * 0.5)

        safety_score = 0.0
        if liquidity >= 100000:
            safety_score += 12.0
        elif liquidity >= 25000:
            safety_score += 8.0
        elif liquidity >= 10000:
            safety_score += 4.0

        moonshot_score = novelty_score + meme_score + social_score + market_score + boost_score + safety_score

        out = {
            "ts": ts,
            "chainId": chain,
            "tokenAddress": addr,
            "symbol": symbol,
            "name": name,
            "liquidity_usd": round(liquidity, 2),
            "volume_h24": round(volume24, 2),
            "price_change_m5": round(price_change_5m, 2),
            "price_change_h1": round(price_change_1h, 2),
            "buys_h1": int(buys_1h),
            "sells_h1": int(sells_1h),
            "pair_age_hours": round(age_hours, 2) if age_hours < 9999 else None,
            "biz_mentions": int(biz_count),
            "x_mentions": int(x_count),
            "boost_amount": round(safe_float(row.get("boost_amount", 0.0)), 2),
            "total_boost": round(safe_float(row.get("total_boost", 0.0)), 2),
            "score": round(moonshot_score, 2),
        }

        # Alert tiers
        if moonshot_score >= 80:
            out["tier"] = "ALERT"
            log(f"ALERT {symbol or addr} score={out['score']} m5={out['price_change_m5']}% h1={out['price_change_h1']}% liq=${out['liquidity_usd']} biz={out['biz_mentions']} x={out['x_mentions']}")
        elif moonshot_score >= 60:
            out["tier"] = "WATCH"
        else:
            out["tier"] = "IGNORE"

        scored.append(out)

        old_state[f"{chain}:{addr}"] = {
            "volume24": volume24,
            "biz_mentions": biz_count,
            "x_mentions": x_count,
            "last_score": moonshot_score,
            "last_seen": ts,
            "symbol": symbol,
            "name": name,
        }

    scored.sort(key=lambda x: x["score"], reverse=True)

    with open(SNAP_FILE, "w", encoding="utf-8") as f:
        json.dump({"ts": ts, "top": scored[:15]}, f, indent=2)

    save_state(old_state)

    print(f"Top moonshot candidates @ {ts}")
    for row in scored[:10]:
        sym = row["symbol"] or row["tokenAddress"][:8]
        print(
            f"{row['tier']:6} "
            f"{sym:10} "
            f"score={row['score']:6} "
            f"m5={row['price_change_m5']:6}% "
            f"h1={row['price_change_h1']:6}% "
            f"liq=${row['liquidity_usd']:10} "
            f"biz={row['biz_mentions']:3} "
            f"x={row['x_mentions']:3}"
        )

if __name__ == "__main__":
    main()
