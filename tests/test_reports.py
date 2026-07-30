"""Reports-layer tests — pagination, search_all_reports (no network)."""
import os

import pytest

from pyerowid.parse import parse_search, parse_search_page_count
from pyerowid.reports import search_all_reports, search_reports

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _read(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return fh.read()


def _has(name):
    return os.path.exists(os.path.join(FIX, name))


# ---------------------------------------------------------------------------
# search_reports pagination kwargs
# ---------------------------------------------------------------------------

def test_search_reports_start_adds_params(monkeypatch):
    """search_reports with start>0 passes Start and Max to the transport."""
    captured = {}

    class FakeTransport:
        def get_html(self, path, **params):
            captured.update(params)
            return "<html></html>"

    search_reports("LSD", start=100, page_size=50, transport=FakeTransport())
    assert captured.get("Start") == 100
    assert captured.get("Max") == 50


def test_search_reports_no_start_no_pagination_params(monkeypatch):
    """search_reports without start does NOT add Start/Max params."""
    captured = {}

    class FakeTransport:
        def get_html(self, path, **params):
            captured.update(params)
            return "<html></html>"

    search_reports("LSD", transport=FakeTransport())
    assert "Start" not in captured
    assert "Max" not in captured


# ---------------------------------------------------------------------------
# search_all_reports auto-pagination
# ---------------------------------------------------------------------------

def test_search_all_reports_single_page(monkeypatch):
    """search_all_reports returns one page when results-table says 1 page."""
    call_log = []

    def fake_get(path, **params):
        call_log.append(dict(params))
        # Return single-page HTML (no results-table → page count = 1)
        if not _has("search_real.html"):
            return "<html></html>"
        # Use real fixture for first call, empty for subsequent
        if not call_log or "Start" not in params:
            return _read("search_real.html")
        return "<html></html>"

    class FakeTransport:
        def get_html(self, path, **params):
            return fake_get(path, **params)

    if not _has("search_real.html"):
        pytest.skip("real fixture not present")

    # synesthesia has 3 pages in the real fixture — cap at 1
    results = search_all_reports("synesthesia", max_pages=1, transport=FakeTransport())
    # Only one page fetched
    assert len([c for c in call_log if "Start" not in c]) == 1
    assert len(results) == 100


def test_search_all_reports_multi_page(monkeypatch):
    """search_all_reports fetches all pages up to max_pages."""
    call_log = []

    if not _has("search_real.html"):
        pytest.skip("real fixture not present")

    page1_html = _read("search_real.html")
    # The real fixture says "Page 1 of 3"; we only have page 1 content.
    # For pages 2+ return an empty result to validate fetching behaviour.
    empty_html = "<html></html>"

    class FakeTransport:
        def get_html(self, path, **params):
            call_log.append(dict(params))
            return page1_html if "Start" not in params else empty_html

    results = search_all_reports("synesthesia", max_pages=2, transport=FakeTransport())
    # page 0 (no Start) + page 1 (Start=100) = 2 fetches
    assert len(call_log) == 2
    assert call_log[1]["Start"] == 100
    # 100 from page 1 + 0 from page 2 (empty)
    assert len(results) == 100


# ---------------------------------------------------------------------------
# parse_search_page_count
# ---------------------------------------------------------------------------

def test_page_count_from_real_fixture():
    if not _has("search_real.html"):
        pytest.skip("real fixture not present")
    assert parse_search_page_count(_read("search_real.html")) == 3


def test_page_count_no_table():
    assert parse_search_page_count("<html><body></body></html>") == 1
