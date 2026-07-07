# Tokyo Event Tracker

Interactive map of current and upcoming Tokyo events (collab cafes, pop-up stores, exhibitions, lives, stage, classical) plotted on OpenStreetMap with category/date/source filters and free-text search.

## Structure

```
index.html          the map app — open directly in a browser
data/
  events_data.js    scraped event data (loaded by index.html)
  venues.js         venue → [lat,lng] geocoding dictionary
scraper.py          refreshes data/events_data.js from all sources
requirements.txt    scraper dependencies
tests/              scraper unit tests (no network): python -m pytest
.github/workflows/
  scrape.yml        daily scheduled scrape (21:00 UTC = 6am JST) that commits data back
```

## Usage

Open `index.html` in a browser. No server needed.

## Refreshing data

```
pip install -r requirements.txt
python scraper.py                 # all sources
python scraper.py --source cc,lp  # only these; other sources keep existing data
```

Then reload `index.html`.

The scraper merges into the existing `data/events_data.js` rather than overwriting it: any source that fails, returns nothing, or shrinks below 50% of its previous count keeps its old data (a warning is printed). It also writes `window.EVENTS_META` with the generation date and per-source counts.

A GitHub Actions workflow (`.github/workflows/scrape.yml`) runs the tests and the scraper daily and commits `data/events_data.js` back if it changed.

## Sources

| Source | Method | Notes |
|---|---|---|
| collabo-cafe.com | Tokyo tag listing pages | cafes, pop-ups, exhibitions |
| t.livepocket.jp | search (pref=13, upcoming) | lives, idol events |
| eplus.jp | search per genre (`todohuken_filter=13&uketsuke_status=1`) | first page per genre only (pagination is JS-driven) |
| l-tike.com | keyword search, data-* attributes | may be bot-blocked; skipped on failure |
| t.pia.jp | keyword search, server-rendered | soft-blocks rapid requests; skipped on failure |

If eplus/l-tike/pia block the scraper, the collabo-cafe + LivePocket refresh still works and existing data for the blocked sources is kept as-is by the merge logic.

## Maintenance notes

- Venue geocoding is a hand-built dictionary (`GEO_VENUES` / `GEO_AREAS`) in `data/venues.js` — add new venues there when pins fall back to district-level "推定位置".
- Category filters are defined in `index.html` (`CAT_LABEL` / `CAT_COLOR` and the header chips).
