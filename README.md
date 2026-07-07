# Tokyo Event Tracker

Interactive map of current and upcoming Tokyo events (collab cafes, pop-up stores, exhibitions, lives, stage, classical) plotted on OpenStreetMap with category/date/source filters and free-text search.

## Structure

```
index.html          the map app — open directly in a browser
data/
  events_data.js    scraped event data (loaded by index.html)
scraper.py          refreshes data/events_data.js from all sources
requirements.txt    scraper dependencies
```

## Usage

Open `index.html` in a browser. No server needed.

## Refreshing data

```
pip install -r requirements.txt
python scraper.py
```

Then reload `index.html`.

## Sources

| Source | Method | Notes |
|---|---|---|
| collabo-cafe.com | Tokyo tag listing pages | cafes, pop-ups, exhibitions |
| t.livepocket.jp | search (pref=13, upcoming) | lives, idol events |
| eplus.jp | search per genre (`todohuken_filter=13&uketsuke_status=1`) | first page per genre only (pagination is JS-driven) |
| l-tike.com | keyword search, data-* attributes | may be bot-blocked; skipped on failure |
| t.pia.jp | keyword search, server-rendered | soft-blocks rapid requests; skipped on failure |

If eplus/l-tike/pia block the scraper, the collabo-cafe + LivePocket refresh still works and existing data for the blocked sources is left as-is (note: the scraper currently overwrites the whole file, so blocked sources come back empty — re-run later or restore from git).

## Maintenance notes

- Venue geocoding is a hand-built dictionary (`GEO_VENUES` / `GEO_AREAS`) in `index.html` — add new venues there when pins fall back to district-level "推定位置".
- Category filters are defined in `index.html` (`CAT_LABEL` / `CAT_COLOR` and the header chips).
