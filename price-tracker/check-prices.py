#!/usr/bin/env python3
"""
Price Tracker - 3-tier price checking system.
Tier 1: Brave Search API
Tier 2: Perplexity Sonar via search.py (fallback)
Tier 3: Failure alert written to alerts.txt
Alerts summary always written to alerts.txt after every run.
"""

import json
import os
import re
import sys
import subprocess
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

TRACKER_DIR = "/mnt/workspace/price-tracker"
SEARCH_TOOL = "/mnt/workspace/tools/search.py"
WATCHLIST_PATH = os.path.join(TRACKER_DIR, "watchlist.json")
HISTORY_PATH = os.path.join(TRACKER_DIR, "price-history.json")
ALERTS_PATH = os.path.join(TRACKER_DIR, "alerts.txt")

BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

# Maps text/URL patterns to canonical retailer keys
RETAILER_PATTERNS = [
    ("amazon",           r"amazon(?:\.com)?"),
    ("tackle_warehouse", r"tackle\s*warehouse(?:\.com)?"),
    ("walmart",          r"walmart(?:\.com)?"),
    ("bass_pro",         r"bass\s*pro(?:\s*shops)?"),
    ("cabelas",          r"cabela'?s?"),
    ("fishusa",          r"fishusa(?:\.com)?"),
    ("tackle_direct",    r"tackle\s*direct(?:\.com)?"),
]

RETAILER_DISPLAY = {
    "amazon":           "Amazon",
    "tackle_warehouse": "TackleWarehouse",
    "walmart":          "Walmart",
    "bass_pro":         "Bass Pro",
    "cabelas":          "Cabela's",
    "fishusa":          "FishUSA",
    "tackle_direct":    "TackleDirect",
}


def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)


def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def detect_retailer_near_price(text, price_start, window=120):
    """Return the canonical retailer key for a price match, searching nearby context."""
    context_start = max(0, price_start - window)
    context = text[context_start : price_start + window].lower()
    for retailer_key, pattern in RETAILER_PATTERNS:
        if re.search(pattern, context, re.IGNORECASE):
            return retailer_key
    return None


def parse_prices(text):
    """
    Extract {retailer: lowest_price} from search response text.
    Skips values outside $5–$2000 and those with no nearby retailer signal.
    """
    prices = {}
    for m in re.finditer(r'\$([0-9]{1,4}(?:\.[0-9]{1,2})?)\b', text):
        amount = float(m.group(1))
        if amount < 5 or amount > 2000:
            continue
        retailer = detect_retailer_near_price(text, m.start())
        if retailer is None:
            continue
        if retailer not in prices or amount < prices[retailer]:
            prices[retailer] = amount
    return prices


# ---------------------------------------------------------------------------
# Tier 1 — Brave Search API
# ---------------------------------------------------------------------------

def query_brave(product_name):
    """
    Query Brave Search API. Returns raw text built from result URLs + snippets,
    or None on any failure/no-results.
    """
    if not BRAVE_API_KEY:
        print("  [Brave] BRAVE_API_KEY not set — skipping Tier 1.")
        return None

    query = f'"{product_name}" price amazon OR tacklewarehouse OR walmart'
    params = urllib.parse.urlencode({"q": query, "count": 10})
    url = f"{BRAVE_SEARCH_URL}?{params}"

    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY,
    })

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  [Brave] HTTP {e.code}: {e.reason}")
        return None
    except Exception as e:
        print(f"  [Brave] Request failed: {e}")
        return None

    results = data.get("web", {}).get("results", [])
    if not results:
        print("  [Brave] No web results returned.")
        return None

    # Build a text blob: URL first (carries retailer signal), then title + snippet
    parts = []
    for r in results:
        parts.append(f"{r.get('url','')} {r.get('title','')} {r.get('description','')}")

    full_text = "\n".join(parts)
    print(f"  [Brave] {len(results)} results ({len(full_text)} chars)")
    return full_text


# ---------------------------------------------------------------------------
# Tier 2 — Perplexity Sonar via search.py
# ---------------------------------------------------------------------------

def query_perplexity(product_name):
    """Call search.py (Perplexity Sonar) and return raw text, or None on failure."""
    query = (
        f"{product_name} price site:amazon.com OR site:tacklewarehouse.com "
        f"OR site:walmart.com 2026"
    )
    try:
        result = subprocess.run(
            [sys.executable, SEARCH_TOOL, query],
            capture_output=True, text=True, timeout=60
        )
        output = result.stdout.strip()
        if result.returncode != 0 or output.startswith("ERROR:") or output.startswith("Error:"):
            print(f"  [Perplexity] Error: {output[:200]}")
            return None
        return output
    except subprocess.TimeoutExpired:
        print("  [Perplexity] Timed out.")
        return None
    except Exception as e:
        print(f"  [Perplexity] Failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Tier orchestration
# ---------------------------------------------------------------------------

def get_prices(product_name):
    """
    Try Tier 1 (Brave) then Tier 2 (Perplexity).
    Returns (prices_dict, tier_label) or (None, None) if both fail.
    """
    print("  [Tier 1] Brave Search API...")
    raw = query_brave(product_name)
    if raw:
        prices = parse_prices(raw)
        if prices:
            print(f"  [Tier 1] Prices found via Brave.")
            return prices, "brave"
        print("  [Tier 1] Results received but no prices parsed.")

    print("  [Tier 2] Perplexity fallback...")
    raw = query_perplexity(product_name)
    if raw:
        preview = raw[:400] + ("..." if len(raw) > 400 else "")
        for line in preview.splitlines():
            print(f"    {line}")
        prices = parse_prices(raw)
        if prices:
            print(f"  [Tier 2] Prices found via Perplexity.")
            return prices, "perplexity"
        print("  [Tier 2] Results received but no prices parsed.")

    return None, None


# ---------------------------------------------------------------------------
# History helpers
# ---------------------------------------------------------------------------

def get_previous_lowest(history, product_id):
    for check in reversed(history.get("checks", [])):
        if check["product_id"] == product_id:
            return check.get("lowest")
    return None


def fmt_retailer(key):
    return RETAILER_DISPLAY.get(key, key.replace("_", " ").title())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    now = datetime.now()
    ts = now.strftime("%Y-%m-%d %H:%M")
    today = now.strftime("%Y-%m-%d")
    print(f"=== Price Check: {ts} ===\n")

    watchlist = load_json(WATCHLIST_PATH)
    history = load_json(HISTORY_PATH)
    active_products = [p for p in watchlist["products"] if p.get("active", True)]

    if not active_products:
        print("No active products on watchlist.")
        return

    threshold_pct = watchlist["settings"].get("alert_threshold_percent", 5)

    # Summary always written to alerts.txt at end of run
    summary_lines = [f"PRICE CHECK - {today}"]

    for product in active_products:
        pid = product["id"]
        name = product["name"]
        target = product.get("target_price")
        print(f"Checking: {name}")

        prices, source = get_prices(name)

        # --- Tier 3: both tiers failed ---
        if prices is None:
            print(f"  *** Both tiers failed for '{name}'")
            summary_lines.append(f"{name}: FAILED - no price found [via Failed] ⚠️")
            print()
            continue

        print("  Parsed prices:")
        for retailer, price in sorted(prices.items()):
            print(f"    {retailer}: ${price:.2f}")

        lowest_retailer = min(prices, key=prices.get)
        lowest_price = prices[lowest_retailer]
        previous_lowest = get_previous_lowest(history, pid)

        change_percent = None
        if previous_lowest:
            change_percent = ((lowest_price - previous_lowest) / previous_lowest) * 100

        tier_key = {"brave": "tier1_brave", "perplexity": "tier2_perplexity"}.get(source, "tier_unknown")
        history["checks"].append({
            "product_id": pid,
            "date": today,
            "prices": prices,
            "lowest": lowest_price,
            "lowest_retailer": lowest_retailer,
            "previous_lowest": previous_lowest,
            "change_percent": round(change_percent, 2) if change_percent is not None else None,
            "source": source,
            "tier": tier_key,
        })

        retailer_display = fmt_retailer(lowest_retailer)
        print(f"  Lowest: ${lowest_price:.2f} at {retailer_display}", end="")
        if change_percent is not None:
            direction = "down" if change_percent < 0 else "up"
            print(f" ({direction} {abs(change_percent):.1f}% from ${previous_lowest:.2f})", end="")
        print()

        # Tier label and URL for alert
        tier_label = {"brave": "via Brave", "perplexity": "via Perplexity"}.get(source, f"via {source}")
        product_url = product.get("urls", {}).get(lowest_retailer)

        # Build summary line
        if change_percent is None or abs(change_percent) < threshold_pct:
            change_str = "no change"
        elif change_percent < -threshold_pct:
            change_str = f"DROP from ${previous_lowest:.2f} ⬇️"
        else:
            change_str = f"UP from ${previous_lowest:.2f} ⬆️"

        alert_line = f"{name}: ${lowest_price:.2f} ({retailer_display}) [{tier_label}] — {change_str}"
        if product_url:
            alert_line += f"\n  {product_url}"
        summary_lines.append(alert_line)

        # Price-drop alert (console only; summary covers alerts.txt)
        if change_percent is not None and change_percent <= -threshold_pct:
            print(
                f"  *** PRICE DROP: {name} dropped {abs(change_percent):.1f}% "
                f"to ${lowest_price:.2f} at {retailer_display} "
                f"(was ${previous_lowest:.2f})"
            )

        # Target-price alert
        if target is not None and lowest_price <= target:
            print(
                f"  *** TARGET HIT: {name} is ${lowest_price:.2f} at {retailer_display} "
                f"(target was ${target:.2f})"
            )

        print()

    # Always append full summary block to alerts.txt
    with open(ALERTS_PATH, 'a') as f:
        f.write("\n".join(summary_lines) + "\n\n")
    print(f"Summary written to {ALERTS_PATH}")

    save_json(HISTORY_PATH, history)
    print(f"Done. {len(active_products)} product(s) checked. History saved.")


if __name__ == "__main__":
    main()
