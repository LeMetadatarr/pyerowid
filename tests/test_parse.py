"""Offline parser tests against real-markup fixtures (no network)."""
import os

from pyerowid.parse import (
    extract_experience_text,
    parse_experience,
    parse_page,
    parse_search,
    parse_search_page_count,
    parse_substance_list,
)
from pyerowid.types import Experience, Report, SubstanceInfo, SubstanceListing

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _read(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return fh.read()


def test_parse_experience():
    exp = parse_experience(_read("experience.html"), 1)
    assert isinstance(exp, Experience)
    assert exp.exp_id == 1
    assert exp.name == "An Unforgettable Ride!"
    assert exp.author == "by Johnny Blaze"
    assert exp.substance == "ecstasy"
    assert exp.year == "2000"
    assert exp.text and len(exp.text) > 100
    assert exp.url == "https://erowid.org/experiences/exp.php?ID=1"
    assert exp.to_dict()["site_id"] == "1"


def test_parse_experience_dosage():
    exp = parse_experience(_read("experience.html"), 1)
    assert len(exp.dosage) == 2
    first = exp.dosage[0]
    assert "0:00" in first.time
    assert first.amount == "0.5 tablets"
    assert first.method == "oral"
    assert first.substance == "mdma"


def test_extract_body_missing():
    assert extract_experience_text("<html>no markers</html>") == ""


def test_parse_experience_empty():
    assert parse_experience("<html><body></body></html>", 999) is None


def test_parse_substance_list():
    listings = parse_substance_list(_read("pharms_list.html"), "https://erowid.org/pharms/")
    assert len(listings) > 10
    assert all(isinstance(s, SubstanceListing) for s in listings)
    first = next(s for s in listings if s.name == "acetaminophen")
    assert first.url.startswith("https://erowid.org/pharms/")
    assert "tylenol" in first.other_names
    assert first.effects


def test_parse_search():
    reports = parse_search(_read("search.html"))
    assert len(reports) > 5
    assert all(isinstance(r, Report) for r in reports)
    r = reports[0]
    assert r.exp_id > 0
    assert r.url.endswith(f"exp.php?ID={r.exp_id}")
    assert r.name and r.substance


def test_parse_search_empty():
    assert parse_search("<html><body>nothing</body></html>") == []


def test_parse_page_substance():
    url = "https://erowid.org/pharms/acetaminophen/acetaminophen.shtml"
    info = parse_page(_read("substance.html"), url)
    assert isinstance(info, SubstanceInfo)
    assert "acetaminophen" in info.name
    assert info.url == "https://erowid.org/pharms/acetaminophen/"
    assert any("tylenol" in n for n in info.other_names)
    assert info.description
    assert info.chem_name
    assert info.effects


# ---------------------------------------------------------------------------
# Real-markup fixtures (captured from Wayback Machine snapshots)
# ---------------------------------------------------------------------------

def _has_fixture(name):
    return os.path.exists(os.path.join(FIX, name))


def test_parse_experience_real():
    """parse_experience works on a real Wayback-captured exp.php page."""
    if not _has_fixture("experience_real.html"):
        import pytest; pytest.skip("real fixture not present")
    exp = parse_experience(_read("experience_real.html"), 1)
    assert isinstance(exp, Experience)
    assert exp.exp_id == 1
    assert exp.name == "An Unforgettable Ride!"
    assert exp.substance == "ecstasy"
    assert exp.year == "2000"
    assert len(exp.dosage) == 2
    assert exp.dosage[0].substance == "mdma"


def test_parse_search_real_no_class_rows():
    """parse_search works on real Wayback page where rows have no CSS class."""
    if not _has_fixture("search_real.html"):
        import pytest; pytest.skip("real fixture not present")
    reports = parse_search(_read("search_real.html"))
    # 100 results per page on this snapshot
    assert len(reports) == 100
    assert all(isinstance(r, Report) for r in reports)
    r0 = reports[0]
    assert r0.exp_id > 0
    assert r0.name
    assert r0.substance


def test_parse_search_page_count_real():
    """parse_search_page_count extracts the total page count from results-table."""
    if not _has_fixture("search_real.html"):
        import pytest; pytest.skip("real fixture not present")
    count = parse_search_page_count(_read("search_real.html"))
    assert count == 3  # "Page 1 of 3" for synesthesia query


def test_parse_search_page_count_single():
    """parse_search_page_count returns 1 when no results-table present."""
    assert parse_search_page_count("<html><body>no table</body></html>") == 1


def test_parse_substance_list_real():
    """parse_substance_list works on real Wayback-captured pharms page."""
    if not _has_fixture("pharms_list_real.html"):
        import pytest; pytest.skip("real fixture not present")
    listings = parse_substance_list(_read("pharms_list_real.html"), "https://erowid.org/pharms/")
    assert len(listings) > 50
    first = next(s for s in listings if s.name == "acetaminophen")
    assert "tylenol" in first.other_names
    assert first.url.endswith("acetaminophen.shtml")


def test_parse_page_substance_real():
    """parse_page works on real Wayback-captured substance vault page."""
    if not _has_fixture("substance_real.html"):
        import pytest; pytest.skip("real fixture not present")
    url = "https://erowid.org/pharms/acetaminophen/acetaminophen.shtml"
    info = parse_page(_read("substance_real.html"), url)
    assert isinstance(info, SubstanceInfo)
    assert "acetaminophen" in info.name
    assert any("tylenol" in n for n in info.other_names)
    assert info.chem_name
    assert info.effects
