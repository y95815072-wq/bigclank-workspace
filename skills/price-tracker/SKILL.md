---
name: price-tracker
description: Track product prices across retailers with daily automated checks and drop alerts. Use when Trey asks to track prices, add items to watchlist, check price history, or find deals.
---

# Price Tracker

You manage a product price watchlist with automated daily checks.

## Files
- Watchlist: /mnt/workspace/price-tracker/watchlist.json
- Price history: /mnt/workspace/price-tracker/price-history.json
- Checker script: /mnt/workspace/price-tracker/check-prices.py
- Alerts: /mnt/workspace/price-tracker/alerts.txt (created when drops detected)

## Commands

### Adding a product
When Trey says "track this" or "add to watchlist" or "watch the price on":
1. Search the web for the product to get the exact name and current price
2. Use CloakBrowser to find the product URL on each working retailer:
   - Amazon (www.amazon.com)
   - Tackle Warehouse (www.tacklewarehouse.com)
   - Walmart (www.walmart.com)
3. Add to watchlist.json with this format:
```json
{
  "id": "short-slug-name",
  "name": "Full Product Name",
  "category": "category-name",
  "target_price": null,
  "urls": {
    "amazon": "full url or null",
    "tackle_warehouse": "full url or null",
    "walmart": "full url or null"
  },
  "added_date": "YYYY-MM-DD",
  "active": true
}
```

4. Confirm to Trey what was added and at what current prices

### Setting a target price
When Trey says "alert me when it drops below $X":
- Update the product's target_price field in watchlist.json

### Removing a product
When Trey says "stop tracking" or "remove from watchlist":
- Set the product's active field to false (don't delete — keep history)

### Checking prices manually
When Trey says "check prices" or "run price check":
```
python3 /mnt/workspace/price-tracker/check-prices.py
```
Report the results.

### Viewing watchlist
When Trey says "show my watchlist" or "what am I tracking":
- Read watchlist.json and display active products with their last known prices from history

### Viewing price history
When Trey says "price history for X" or "how has the price changed":
- Filter price-history.json for that product
- Show a timeline of prices with dates and which retailer was cheapest

### During Heartbeat
Check if /mnt/workspace/price-tracker/alerts.txt exists.
If it does, read it and send the alerts to Trey. Then delete the file.

## Rules
- Always use CloakBrowser (not regular OpenClaw browser) for retailer sites
- Never make a purchase without Trey's explicit confirmation
- If a retailer blocks you, note it and check the others
- Keep the watchlist clean — use slugs for IDs, full names for display
- When adding products, try to get URLs from at least 2 retailers