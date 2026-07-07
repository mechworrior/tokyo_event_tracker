#!/usr/bin/env python3
"""
Tokyo Events scraper — regenerates data/events_data.js for index.html

Sources:
  - collabo-cafe.com  (collab cafes, pop-up stores, exhibitions — Tokyo tag)
  - t.livepocket.jp   (concerts / lives / idol events — Tokyo prefecture, upcoming)
  - eplus.jp          (Tokyo, on-sale, per genre: music/anime/art/stage/event)
  - l-tike.com        (keyword search — may be blocked by bot protection; skipped on failure)
  - t.pia.jp          (keyword search — may be blocked by bot protection; skipped on failure)

Usage:
  pip install -r requirements.txt
  python scraper.py                 # all sources
  python scraper.py --source cc,lp  # only these; others keep existing data
Then reload index.html in your browser.

Sources that fail, return nothing, or shrink below 50% of their previous
count keep their previous data (the existing events_data.js is merged in).

Be polite: this sleeps between requests. Run at most a few times per day.
Note: eplus/l-tike/pia only expose the first page of results to simple scrapers
(pagination is JS-driven), so those sources yield a curated top slice, not everything.
"""
import argparse
import json
import re
import time
import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (personal Tokyo events map; contact: me)"}
SLEEP = 1.0  # seconds between requests
TODAY = datetime.date.today()
OUT_FILE = Path(__file__).resolve().parent / "data" / "events_data.js"


def get(url, tries=2, backoff=3.0):
    """GET with a simple retry + backoff. Returns page text or None."""
    for attempt in range(1, tries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            time.sleep(SLEEP)
            if r.status_code == 200:
                return r.text
            print(f"  ! {r.status_code} {url}")
        except requests.RequestException as e:
            print(f"  ! {type(e).__name__} {url}")
        if attempt < tries:
            time.sleep(backoff * attempt)
    return None


# ---------------- collabo-cafe ----------------
CC_TYPES = ["cafe", "pop-up-store", "gengaten-tenjikai", "kuji", "shop-tieup",
            "theme-park", "event", "goods", "fashion", "comics-release", "new-anime", "news"]


def cc_listing(pages=5):
    events = []
    for p in range(1, pages + 1):
        url = "https://collabo-cafe.com/events/tag/tokyo/" if p == 1 else f"https://collabo-cafe.com/events/tag/tokyo/page/{p}/"
        html = get(url)
        if not html:
            break
        soup = BeautifulSoup(html, "html.parser")
        for art in soup.select("article.event"):
            classes = art.get("class", [])
            link = art.select_one('a[rel="bookmark"]')
            img = art.select_one("img")
            if not link:
                continue
            cats = [c[15:] for c in classes if c.startswith("event-category-")]
            events.append({
                "title": (link.get("title") or link.get_text(strip=True))[:70],
                "url": link["href"],
                "img": (img.get("data-src") or img.get("src") or "") if img else "",
                "cat": next((c for c in cats if c in CC_TYPES), "event"),
            })
        print(f"collabo-cafe page {p}: {len(events)} total")
    seen, out = set(), []
    for e in events:
        if e["url"] not in seen:
            seen.add(e["url"])
            out.append(e)
    return out


def cc_detail(url):
    html = get(url)
    if not html:
        return {}
    soup = BeautifulSoup(html, "html.parser")
    out = {}
    for tr in soup.select("table tr"):
        cells = tr.find_all(["th", "td"])
        if len(cells) < 2:
            continue
        k = cells[0].get_text(strip=True)
        v = re.sub(r"\s+", " ", cells[-1].get_text(" ", strip=True))
        if re.search(r"開催場所|場所|会場", k):
            out["venue"] = (out.get("venue", "") + " / " if out.get("venue") else "") + v
        if re.search(r"開催期間|期間|開催日", k) and "period" not in out:
            out["period"] = v
    return out


def parse_period(p):
    if not p:
        return None, None
    ms = re.findall(r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日", p)
    if not ms:
        return None, None
    y1 = ms[0][0] or str(TODAY.year)
    d1 = f"{y1}-{int(ms[0][1]):02d}-{int(ms[0][2]):02d}"
    d2 = None
    if len(ms) > 1:
        last = ms[-1]
        y2 = last[0] or y1
        if not last[0] and int(last[1]) < int(ms[0][1]):
            y2 = str(int(y1) + 1)
        d2 = f"{y2}-{int(last[1]):02d}-{int(last[2]):02d}"
    return d1, d2


def scrape_collabocafe():
    rows = []
    events = cc_listing()
    for i, e in enumerate(events):
        det = cc_detail(e["url"])
        d1, d2 = parse_period(det.get("period"))
        slug = e["url"].replace("https://collabo-cafe.com/events/collabo/", "").replace("https://collabo-cafe.com", "").rstrip("/")
        img = e["img"].replace("https://collabo-cafe.com/wp-content/uploads/", "")
        rows.append([e["title"], slug, img, e["cat"], det.get("venue", "")[:90], d1, d2])
        print(f"  [{i+1}/{len(events)}] {e['title'][:40]}")
    return rows


# ---------------- LivePocket ----------------
GENRES = ["音楽", "邦楽", "洋楽", "アイドル", "ファン・アイドル", "その他", "演劇・舞台", "お笑い・エンタメ",
          "アニメ・ゲーム", "スポーツ", "クラシック", "ダンス", "DJ・クラブ", "トークショー", "ファッション", "映画", "イベント"]


def scrape_livepocket(max_pages=8):
    rows = []
    for p in range(1, max_pages + 1):
        html = get(f"https://t.livepocket.jp/event/search?pref=13&timespec=after_this&page={p}")
        if not html:
            break
        soup = BeautifulSoup(html, "html.parser")
        found = 0
        for a in soup.select('a[href*="/e/"]'):
            c = a.find_parent(["li", "article", "section"]) or a.parent
            txt = re.sub(r"\s+", " ", c.get_text(" ", strip=True))
            if len(txt) < 30:
                continue
            m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日\([月火水木金土日]\)\s*(\d{1,2}:\d{2})?", txt)
            if not m:
                continue
            date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            if date < TODAY.isoformat():
                continue
            status = (re.match(r"^(売切れ|販売終了|終了|受付中|販売中)", txt) or [None])
            status = status.group(1) if status and hasattr(status, "group") else ""
            title = re.sub(r"^(売切れ|販売終了|終了|受付中|販売中)\s*", "", txt)
            title = re.sub(r"^\d{1,2}/\d{1,2}\s+\d{1,2}:\d{2}\s*", "", title)
            title = re.split(r"\d{4}年\d{1,2}月", title)[0].strip()
            after = txt.split("東京都", 1)[1].strip() if "東京都" in txt else ""
            parts = [x for x in after.split(" ") if x]
            gparts = []
            while parts and all(x.strip() in GENRES for x in parts[-1].rstrip(",").split(",")):
                gparts.insert(0, parts.pop())
            img_el = c.select_one("img")
            img = (img_el.get("data-src") or img_el.get("src") or "").split("?")[0] if img_el else ""
            img = img.replace("https://cdn.livepocket.jp/c!/a=0,u=0,w=233/image/", "")
            href = a.get("href", "").replace("https://t.livepocket.jp", "")
            rows.append({"t": title, "d": date, "tm": m.group(4), "st": status,
                         "v": " ".join(parts), "g": " ".join(gparts), "u": href, "i": img})
            found += 1
        print(f"livepocket page {p}: +{found}")
        if found == 0 and p > 1:
            break
    seen, out = set(), []
    for e in rows:
        if e["u"] not in seen:
            seen.add(e["u"])
            out.append(e)
    return out


# ---------------- eplus ----------------
EPLUS_GENRES = {"100": "music", "800": "anime", "300": "exhibit", "400": "stage", "200": "other"}


def scrape_eplus():
    """First page per genre, Tokyo, on-sale (uketsuke_status=1). Dedupes ticket slots by title+venue."""
    rows, seen = [], set()
    for code, group in EPLUS_GENRES.items():
        url = (f"https://eplus.jp/sf/search?block=true&todohuken_filter=13"
               f"&koen_from_filter={TODAY.year}/{TODAY.month:02d}/{TODAY.day:02d}"
               f"&p_genre_filter={code}&uketsuke_status=1")
        html = get(url)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select("a.ticket-item"):
            h = a.select_one(".ticket-item__header")
            c = a.select_one(".ticket-item__content")
            if not h or not c:
                continue
            title = re.sub(r"^(先着|抽選)\s*", "", re.sub(r"\s+", " ", h.get_text(" ", strip=True)))
            txt = re.sub(r"\s+", " ", c.get_text(" ", strip=True))
            m = re.match(r"^(.*?)（東京都）\s*(.*)$", txt)
            venue, rest = (m.group(1), m.group(2)) if m else (txt, "")
            st = (re.search(r"受付中|受付終了|受付前", rest) or [""])
            st = st.group(0) if hasattr(st, "group") else ""
            if st == "受付終了":
                continue
            dt = (re.search(r"\d{4}/\d{1,2}/\d{1,2}(?:～[\d/]+)?|期間中有効", rest) or [""])
            dt = dt.group(0) if hasattr(dt, "group") else ""
            key = title[:40] + "|" + venue[:20]
            if key in seen:
                continue
            seen.add(key)
            href = a.get("href", "").split("?")[0].replace("/sf/detail/", "")
            g = {"anime": "exhibit"}.get(group, group)
            rows.append({"t": title[:60], "v": venue[:35], "dt": dt, "st": st, "u": href, "g": g})
        print(f"eplus genre {code}: total {len(rows)}")
    return rows


# ---------------- l-tike ----------------
def scrape_ltike():
    """Keyword search page; event data lives in data-* attributes. May be bot-blocked."""
    rows = []
    try:
        html = get("https://l-tike.com/search/?keyword=%E6%9D%B1%E4%BA%AC")
        if not html:
            return rows
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select("a[data-lcode]"):
            name = a.get("data-prfname", "")
            venue = a.get("data-basevenuename", "").replace("　", " ")
            dates = [d for d in a.get("data-prfdate", "").split(",") if d]
            if not name or not dates:
                continue
            if dates[-1] < TODAY.strftime("%Y%m%d"):
                continue
            rows.append({"t": name[:60], "v": venue[:35], "d1": dates[0], "d2": dates[-1],
                         "c": "classic", "st": "", "l": a.get("data-lcode")})
        # dedupe by lcode+venue
        seen, out = set(), []
        for r in rows:
            k = r["l"] + r["v"]
            if k not in seen:
                seen.add(k)
                out.append(r)
        rows = out
    except Exception as e:
        print(f"l-tike failed ({e}) — skipping")
    print(f"l-tike: {len(rows)}")
    return rows


# ---------------- pia ----------------
def scrape_pia():
    """Keyword search; server-rendered ul.table_data rows. May be bot-blocked."""
    rows = []
    try:
        html = get("https://t.pia.jp/pia/search_all.do?kw=%E6%9D%B1%E4%BA%AC%E9%83%BD")
        if not html:
            return rows
        soup = BeautifulSoup(html, "html.parser")
        for u in soup.select("ul.table_data"):
            txt = re.sub(r"\s+", " ", u.get_text(" ", strip=True))
            m = re.match(r"^(?:[^／]{0,20}／)?(.*?)\s*(\d{4}/\d{1,2}/\d{1,2})\([^)]+\)"
                         r"(?:\s*[～〜]\s*(\d{4}/\d{1,2}/\d{1,2})\([^)]+\))?\s*(.*?)\s*[（(]東京都[)）]"
                         r"\s*(販売期間中|販売前|受付中|販売終了)?", txt)
            if not m:
                continue
            rows.append({"t": m.group(1)[:60], "d1": m.group(2), "d2": m.group(3) or m.group(2),
                         "v": m.group(4)[:35], "st": m.group(5) or "", "c": "music"})
    except Exception as e:
        print(f"pia failed ({e}) — skipping")
    print(f"pia: {len(rows)}")
    return rows


# ---------------- merge / write ----------------
# source key -> (JS global suffix, scrape function)
SOURCES = {
    "cc": ("CC", scrape_collabocafe),
    "lp": ("LP", scrape_livepocket),
    "ep": ("EP", scrape_eplus),
    "lt": ("LT", scrape_ltike),
    "pia": ("PIA", scrape_pia),
}
KEEP_RATIO = 0.5  # keep old data if new scrape yields < 50% of previous count


def load_existing(path):
    """Parse window.EVENTS_XX arrays out of an existing events_data.js.

    Returns {source_key: list}. Missing file / unparseable arrays are simply
    absent from the result. Handles multi-line arrays.
    """
    path = Path(path)
    out = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    dec = json.JSONDecoder()
    for key, (suffix, _) in SOURCES.items():
        m = re.search(r"window\.EVENTS_%s\s*=\s*" % suffix, text)
        if not m:
            continue
        try:
            val, _end = dec.raw_decode(text, m.end())
        except ValueError:
            continue
        if isinstance(val, list):
            out[key] = val
    return out


def choose(old, new, name=""):
    """Pick new data unless the scrape failed/shrank badly; then keep old."""
    old = old or []
    if new is None:
        print(f"  ! {name}: scrape failed — keeping previous {len(old)} events")
        return old
    if old and len(new) == 0:
        print(f"  ! {name}: scrape returned 0 events — keeping previous {len(old)}")
        return old
    if old and len(new) < KEEP_RATIO * len(old):
        print(f"  ! {name}: only {len(new)} events (was {len(old)}) — keeping previous data")
        return old
    return new


def write_data(path, data, meta):
    """Write data/events_data.js. data = {source_key: list}, meta = dict."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"// Tokyo Events data — generated {meta.get('generated', '')} by scraper.py\n")
        for key, (suffix, _) in SOURCES.items():
            f.write(f"window.EVENTS_{suffix} = "
                    + json.dumps(data.get(key, []), ensure_ascii=False) + ";\n")
        f.write("window.EVENTS_META = " + json.dumps(meta, ensure_ascii=False) + ";\n")


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Refresh data/events_data.js")
    ap.add_argument("--source", default=",".join(SOURCES),
                    help="comma-separated sources to scrape (%s); others keep "
                         "existing data" % ",".join(SOURCES))
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    wanted = [s.strip() for s in args.source.split(",") if s.strip()]
    bad = [s for s in wanted if s not in SOURCES]
    if bad:
        raise SystemExit(f"unknown source(s): {', '.join(bad)} (valid: {', '.join(SOURCES)})")

    existing = load_existing(OUT_FILE)
    merged = {}
    for key, (_, scrape) in SOURCES.items():
        old = existing.get(key, [])
        if key not in wanted:
            print(f"{key}: not requested — keeping existing {len(old)} events")
            merged[key] = old
            continue
        print(f"Scraping {key}...")
        try:
            new = scrape()
        except Exception as e:
            print(f"  ! {key} scrape crashed: {type(e).__name__}: {e}")
            new = None
        merged[key] = choose(old, new, key)
        print(f"→ {key}: {len(merged[key])} events\n")

    meta = {"generated": TODAY.isoformat(),
            "counts": {k: len(v) for k, v in merged.items()}}
    write_data(OUT_FILE, merged, meta)
    print(f"Wrote {OUT_FILE} — reload index.html")


if __name__ == "__main__":
    main()
