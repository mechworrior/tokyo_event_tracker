"""Unit tests for scraper.py — no network access required."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scraper  # noqa: E402


# ---------------- parse_period ----------------

def test_parse_period_full_range():
    assert scraper.parse_period("2026年7月1日～2026年7月31日") == ("2026-07-01", "2026-07-31")


def test_parse_period_end_year_omitted():
    assert scraper.parse_period("2026年7月1日～8月15日") == ("2026-07-01", "2026-08-15")


def test_parse_period_year_wrap():
    # end month earlier than start month with no year → next year
    assert scraper.parse_period("2026年12月20日～1月5日") == ("2026-12-20", "2027-01-05")


def test_parse_period_single_date():
    assert scraper.parse_period("2026年9月3日") == ("2026-09-03", None)


def test_parse_period_no_year_uses_today():
    d1, d2 = scraper.parse_period("7月1日～7月31日")
    y = str(scraper.TODAY.year)
    assert d1 == f"{y}-07-01" and d2 == f"{y}-07-31"


def test_parse_period_empty_or_garbage():
    assert scraper.parse_period(None) == (None, None)
    assert scraper.parse_period("") == (None, None)
    assert scraper.parse_period("開催中") == (None, None)


# ---------------- choose (merge decision) ----------------

OLD = [{"t": f"old{i}"} for i in range(10)]


def test_choose_uses_new_when_healthy():
    new = [{"t": f"new{i}"} for i in range(9)]
    assert scraper.choose(OLD, new, "x") is new


def test_choose_keeps_old_on_failure():
    assert scraper.choose(OLD, None, "x") == OLD


def test_choose_keeps_old_on_empty():
    assert scraper.choose(OLD, [], "x") == OLD


def test_choose_keeps_old_on_big_shrink():
    new = [{"t": "new"}] * 4  # 4 < 50% of 10
    assert scraper.choose(OLD, new, "x") == OLD


def test_choose_accepts_exactly_half():
    new = [{"t": "new"}] * 5  # 5 == 50% of 10 → accepted
    assert scraper.choose(OLD, new, "x") is new


def test_choose_new_when_no_old():
    new = [{"t": "new"}]
    assert scraper.choose([], new, "x") is new
    assert scraper.choose(None, new, "x") is new
    assert scraper.choose(None, None, "x") == []


# ---------------- write_data / load_existing roundtrip ----------------

SAMPLE = {
    "cc": [["タイトル", "slug", "img.jpg", "cafe", "渋谷", "2026-07-01", "2026-07-31"]],
    "lp": [{"t": "ライブ", "d": "2026-08-01", "u": "/e/x"}],
    "ep": [{"t": "展示", "v": "上野の森美術館"}],
    "lt": [],
    "pia": [{"t": "コンサート", "d1": "2026/7/6"}],
}
META = {"generated": "2026-07-08", "counts": {k: len(v) for k, v in SAMPLE.items()}}


def test_write_then_load_roundtrip(tmp_path):
    out = tmp_path / "events_data.js"
    scraper.write_data(out, SAMPLE, META)
    loaded = scraper.load_existing(out)
    assert loaded == SAMPLE


def test_write_emits_all_globals_and_meta(tmp_path):
    out = tmp_path / "events_data.js"
    scraper.write_data(out, SAMPLE, META)
    text = out.read_text(encoding="utf-8")
    for suffix in ("CC", "LP", "EP", "LT", "PIA", "META"):
        assert f"window.EVENTS_{suffix} = " in text
    assert '"generated": "2026-07-08"' in text
    assert text.rstrip().endswith(";")


def test_load_existing_missing_file(tmp_path):
    assert scraper.load_existing(tmp_path / "nope.js") == {}


def test_load_existing_multiline_arrays(tmp_path):
    # hand-formatted file with one object per line, like the original data file
    out = tmp_path / "events_data.js"
    out.write_text(
        "// comment\n"
        "window.EVENTS_CC = [];\n"
        "window.EVENTS_EP = [\n"
        '{"t":"a","v":"x"},\n'
        '{"t":"b","v":"y"}\n'
        "];\n",
        encoding="utf-8",
    )
    loaded = scraper.load_existing(out)
    assert loaded["cc"] == []
    assert loaded["ep"] == [{"t": "a", "v": "x"}, {"t": "b", "v": "y"}]
    assert "lp" not in loaded
