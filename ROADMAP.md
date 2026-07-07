# Roadmap

Assessment of the current state and a phased plan. Current: single-page Leaflet map (`index.html`) reading JS globals from `data/events_data.js`, refreshed by `scraper.py` (5 sources, 3 of them bot-protected and flaky). Works fully offline from `file://` — that's a feature worth preserving, and why data is a `.js` file rather than fetched JSON (no CORS).

## Known weaknesses

1. **Data loss on blocked sources.** `scraper.py` overwrites the whole data file; if eplus/l-tike/pia are blocked that run, their events vanish. Should merge: keep the previous array when a source returns empty.
2. **Geocoding is a hand-maintained dictionary inside `index.html`.** ~150 venues hardcoded in app code. Every new venue means editing the app. Should live in its own file (`data/venues.js`), ideally auto-grown by the scraper via Nominatim (OSM) lookups with a local cache.
3. **No safety net.** collabo-cafe/livepocket scrapers aren't wrapped in try/except (one site change kills the whole run); no validation before overwriting good data; no parser tests.
4. **No freshness visibility.** The UI doesn't show when data was last scraped or how many events each source contributed.
5. **Cross-source duplicates.** The same concert can appear via eplus and pia; no dedupe across sources.

## Phase 1 — hardening (small, high value)

- [ ] Merge-not-overwrite in `scraper.py`: parse existing `events_data.js`, keep old data for any source that fails or returns suspiciously few results (e.g. <50% of previous count)
- [ ] Wrap every source in try/except; add `--source cc,lp,...` flag to refresh selectively; retry with backoff
- [ ] Show "data generated YYYY-MM-DD" + per-source counts in the map header
- [ ] Move `GEO_VENUES`/`GEO_AREAS` to `data/venues.js`; scraper prints venues that failed to geocode
- [ ] Parser unit tests against saved HTML fixtures (`tests/fixtures/`)

## Phase 2 — usability features

- [ ] Favorites/watchlist (localStorage) with a ★ filter
- [ ] "Open in Google Maps" + station/directions link in popups
- [ ] Export event to calendar (.ics download)
- [ ] Date-range picker and a simple calendar/list-by-week view
- [ ] Geolocation "near me" filter (distance rings)
- [ ] Cross-source dedupe (fuzzy title + venue + date match)

## Phase 3 — data expansion & automation

- [ ] New sources: Tokyo Art Beat (exhibitions), Peatix, connpass (tech), Walkerplus, Time Out Tokyo
- [ ] Automated Nominatim geocoding with persistent cache (`data/geocode_cache.json`) — retire manual dictionary upkeep
- [ ] Scheduled refresh (daily) + "new since last visit" highlight
- [ ] Keyword alerts: flag new events matching watched terms (e.g. an artist or franchise)
- [ ] Track ticket status over time (on-sale → sold out) to surface "selling fast"

## Non-goals (for now)

- Backend/server — the `file://` zero-install model is the point
- Scraping full eplus pagination (JS-driven; needs a real browser; current top-slice-per-genre is an accepted trade-off)
