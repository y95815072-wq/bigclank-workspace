#!/usr/bin/env python3
"""
Price Tracker - uses Perplexity Sonar via search.py to find current prices.
No browser scraping. Run manually or via cron.
"""

import json
import os
import re
import sys
import subprocess
from datetime import datetime

TRACKER_DIR = "/mnt/workspace/price-tracker"
SEARCH_TOOL = "/mnt/workspace/tools/search.py"
WATCHLIST_PATH = os.path.join(TRACKER_DIR, "watchlist.json")
HISTORY_PATH = os.path.join(TRACKER_DIR, "price-history.json")
ALERTS_PATH = os.path.join(TRACKER_DIR, "alerts.txt")

# Maps text patterns found in Perplexity output to canonical retailer keys
RETAILER_PATTERNS = [
    ("amazon",          r"amazon(?:\.com)?"),
    ("tackle_warehouse", r"tackle\s*warehouse(?:\.com)?"),
    ("walmart",         r"walmart(?:\.com)?"),
    ("bass_pro",        r"bass\s*pro(?:\s*shops)?"),
    ("cabelas",         r"cabela'?s?"),
    ("fishusa",         r"fishusa(?:\.com)?"),
    ("tackle_direct",   r"tackle\s*direct(?:\.com)?"),
]


def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)


def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def append_alert(message):
    with open(ALERTS_PATH, 'a') as f:
        f.write(message + "\n")


def query_perplexity(product_name):
    """Call search.py and return the raw text response."""
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
            print(f"  Search error: {output[:200]}")
            return None
        return output
    except subprocess.TimeoutExpired:
        print("  Search timed out.")
        return None
    except Exception as e:
        print(f"  Search failed: {e}")
        return None


def detect_retailer_near_price(text, price_start, window=120):
    """Return the best-matching retailer name for a price found at price_start."""
    # Search within a window before the price match
    context_start = max(0, price_start - window)
    context = text[context_start : price_start + window].lower()

    for retailer_key, pattern in RETAILER_PATTERNS:
        if re.search(pattern, context, re.IGNORECASE):
            return retailer_key

    return None


def parse_prices(text):
    """
    Extract (retailer, price) pairs from Perplexity response text.
    Returns dict: {retailer: lowest_price_seen_for_that_retailer}
    """
    prices = {}

    # Find all dollar amounts like $179.99 or $12
    for m in re.finditer(r'\$([0-9]{1,4}(?:\.[0-9]{1,2})?)\b', text):
        amount = float(m.group(1))
        # Sanity filter: skip obviously wrong values (shipping costs, tiny accessories)
        if amount < 5 or amount > 2000:
            continue

        retailer = detect_retailer_near_price(text, m.start())
        if retailer is None:
            continue

        # Keep the lowest price seen per retailer
        if retailer not in prices or amount < prices[retailer]:
            prices[retailer] = amount

    return prices


def get_previous_lowest(history, product_id):
    for check in reversed(history.get("checks", [])):
        if check["product_id"] == product_id:
            return check.get("lowest")
    return None


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

    for product in active_products:
        pid = product["id"]
        name = product["name"]
        target = product.get("target_price")
        print(f"Checking: {name}")

        raw = query_perplexity(name)

        if not raw:
            msg = f"[{ts}] FAILURE: No Perplexity response for '{name}' (id={pid})"
            print(f"  *** {msg}")
            append_alert(msg)
            print()
            continue

        print(f"  Raw response ({len(raw)} chars):")
        # Print first 600 chars so output is readable
        preview = raw[:600] + ("..." if len(raw) > 600 else "")
        for line in preview.splitlines():
            print(f"    {line}")
        print()

        prices = parse_prices(raw)

        if not prices:
            msg = f"[{ts}] FAILURE: Could not parse any prices for '{name}' (id={pid})"
            print(f"  *** {msg}")
            append_alert(msg)
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

        check_entry = {
            "product_id": pid,
            "date": today,
            "prices": prices,
            "lowest": lowest_price,
            "lowest_retailer": lowest_retailer,
            "previous_lowest": previous_lowest,
            "change_percent": round(change_percent, 2) if change_percent is not None else None,
        }
        history["checks"].append(check_entry)

        print(f"  Lowest: ${lowest_price:.2f} at {lowest_retailer}", end="")
        if change_percent is not None:
            direction = "down" if change_percent < 0 else "up"
            print(f" ({direction} {abs(change_percent):.1f}% from ${previous_lowest:.2f})", end="")
        print()

        # Alert: price drop below threshold vs previous lowest
        if (change_percent is not None
                and change_percent <= -threshold_pct):
            msg = (
                f"[{ts}] PRICE DROP: {name} dropped {abs(change_percent):.1f}% "
                f"to ${lowest_price:.2f} at {lowest_retailer} "
                f"(was ${previous_lowest:.2f})"
            )
            print(f"  *** {msg}")
            append_alert(msg)

        # Alert: price at or below target_price
        if target is not None and lowest_price <= target:
            msg = (
                f"[{ts}] TARGET HIT: {name} is ${lowest_price:.2f} at {lowest_retailer} "
                f"(target was ${target:.2f})"
            )
            print(f"  *** {msg}")
            append_alert(msg)

        print()

    save_json(HISTORY_PATH, history)
    print(f"Done. {len(active_products)} product(s) checked. History saved.")


if __name__ == "__main__":
    main()
