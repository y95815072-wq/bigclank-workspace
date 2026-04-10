# Price Tracker — System Documentation

## What It Does

Monitors fishing gear prices across retailers daily. Detects price drops/increases, logs history, and writes a summary alert file after every run.

## Files

| File | Purpose |
|---|---|
| `check-prices.py` | Main runner — 3-tier price fetch + alert generation |
| `watchlist.json` | Products to track + retailer URLs + alert threshold |
| `price-history.json` | All historical price checks |
| `alerts.txt` | Latest run summary (overwritten/appended each run) |

## 3-Tier System

```
Tier 1: Brave Search API
  → Queries: "<product>" price amazon OR tacklewarehouse OR walmart
  → Builds text blob from result URL + title + description
  → parse_prices() extracts $X.XX with retailer context (window=120 chars)
  → Filters out prices outside $5–$2000
  → If prices found: returns (prices_dict, "brave")

Tier 2: Perplexity (search.py fallback)
  → Runs: python3 /mnt/workspace/tools/search.py "<query>"
  → parse_prices() same logic applied to Perplexity response text
  → If prices found: returns (prices_dict, "perplexity")

Tier 3: Failure
  → Both tiers failed — logs "FAILED - no price found [via Failed] ⚠️"
  → Returns (None, None)
```

## Alert Format

```
PRICE CHECK - 2026-04-10
Dobyns Fury FR 735C Casting Rod: $149.99 (TackleWarehouse) [via Perplexity] — DROP from $179.99 ⬇️
  https://www.tacklewarehouse.com/Dobyns_Fury_Casting_Rods/descpage-DFC.html

SomeOtherRod: $XX.XX (Retailer) [via Brave] — no change
  https://...

FailedRod: FAILED - no price found [via Failed] ⚠️
```

- `[via Brave]` — price came from Tier 1 (Brave Search API)
- `[via Perplexity]` — price came from Tier 2 (Perplexity fallback)
- `[via Failed]` — both tiers failed
- URL is pulled from `watchlist.json` → `urls.<retailer>` for the lowest-price retailer
- URL line is omitted if no matching URL in watchlist

## Cron Schedule

| Time (UTC) | Job |
|---|---|
| 1:00 PM | `check-prices.py` — fetch prices, write/append alerts.txt |
| 1:05 PM | Alert dispatch (send alerts.txt via Telegram) |

## Retailer Detection

Regex patterns used to identify retailers from nearby text context:

| Key | Display | Pattern |
|---|---|---|
| `amazon` | Amazon | `amazon(?:\.com)?` |
| `tackle_warehouse` | TackleWarehouse | `tackle\s*warehouse(?:\.com)?` |
| `walmart` | Walmart | `walmart(?:\.com)?` |
| `bass_pro` | Bass Pro | `bass\s*pro(?:\s*shops)?` |
| `cabelas` | Cabela's | `cabela'?s?` |
| `fishusa` | FishUSA | `fishusa(?:\.com)?` |
| `tackle_direct` | TackleDirect | `tackle\s*direct(?:\.com)?` |

## Watchlist Format (watchlist.json)

```json
{
  "products": [
    {
      "id": "dobyns-fury-735c",
      "name": "Dobyns Fury FR 735C Casting Rod",
      "category": "fishing-rods",
      "target_price": null,
      "urls": {
        "amazon": "https://www.amazon.com/s?k=Dobyns+Fury+735C",
        "tackle_warehouse": "https://www.tacklewarehouse.com/...",
        "walmart": "https://www.walmart.com/ip/..."
      },
      "added_date": "2026-04-07",
      "active": true
    }
  ],
  "settings": {
    "alert_threshold_percent": 5,
    "check_frequency": "daily",
    "alert_channel": "telegram"
  }
}
```

## Notes

- Old browser/Chromium scraping is fully removed — replaced by the Brave+Perplexity API tiers
- Price history saves `source` and `tier` fields for every check entry
- Alerts are always written after every run (daily summary behavior)
- UP alerts fire when price rises ≥ threshold%, not just drops
- History uses `/mnt/workspace/price-tracker/` paths; SKILL.md and code live in the git workspace
