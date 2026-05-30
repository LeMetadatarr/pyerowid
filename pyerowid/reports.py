"""Experience and substance-vault lookups backed by erowid.org.

Erowid has no JSON API, so this scrapes HTML (see :mod:`pyerowid.parse`). Every
function takes an optional ``transport`` and falls back to the shared
environment-driven one.
"""
from __future__ import annotations

import random
from typing import List, Optional

from pyerowid._transport import Transport, default_transport
from pyerowid.parse import (
    parse_categories,
    parse_experience,
    parse_page,
    parse_search,
    parse_search_page_count,
    parse_substance_list,
)
from pyerowid.types import Experience, Report, SubstanceInfo, SubstanceListing

# Highest experience id observed; random_experience samples below it.
MAX_EXPERIENCE_ID = 111451

_CATEGORY_BASES = {
    "pharms": "https://erowid.org/pharms/",
    "chemicals": "https://erowid.org/chemicals/",
    "plants": "https://erowid.org/plants/",
    "herbs": "https://erowid.org/herbs/",
    "smarts": "https://erowid.org/smarts/",
    "animals": "https://erowid.org/animals/",
}


def _t(transport: Optional[Transport]) -> Transport:
    return transport or default_transport()


def get_experience(exp_id: int, *, transport: Optional[Transport] = None) -> Optional[Experience]:
    """Fetch a single experience report by id (``None`` if it has no report).

    Example::

        import pyerowid
        exp = pyerowid.get_experience(1)
        print(exp.name, exp.substance, exp.year)
    """
    try:
        html = _t(transport).get_html("/experiences/exp.php", ID=exp_id)
    except Exception:
        return None
    try:
        return parse_experience(html, int(exp_id))
    except Exception:
        return None


def get_categories(*, transport: Optional[Transport] = None) -> List[str]:
    """List the experience-report substance categories."""
    html = _t(transport).get_html("/experiences/exp_list.shtml")
    return parse_categories(html)


def _extract_list(category: str, *, transport: Optional[Transport] = None) -> List[SubstanceListing]:
    base_url = _CATEGORY_BASES[category]
    return parse_substance_list(_t(transport).get_html(base_url), base_url)


def get_pharms(*, transport: Optional[Transport] = None) -> List[SubstanceListing]:
    """List the pharmaceutical vault index."""
    return _extract_list("pharms", transport=transport)


def get_chemicals(*, transport: Optional[Transport] = None) -> List[SubstanceListing]:
    """List the chemical vault index."""
    return _extract_list("chemicals", transport=transport)


def get_plants(*, transport: Optional[Transport] = None) -> List[SubstanceListing]:
    """List the plant vault index."""
    return _extract_list("plants", transport=transport)


def get_herbs(*, transport: Optional[Transport] = None) -> List[SubstanceListing]:
    """List the herb vault index."""
    return _extract_list("herbs", transport=transport)


def get_smarts(*, transport: Optional[Transport] = None) -> List[SubstanceListing]:
    """List the smart-products vault index."""
    return _extract_list("smarts", transport=transport)


def get_animals(*, transport: Optional[Transport] = None) -> List[SubstanceListing]:
    """List the animal vault index."""
    return _extract_list("animals", transport=transport)


def parse_substance_page(url: str, *, transport: Optional[Transport] = None) -> SubstanceInfo:
    """Fetch and parse a substance vault summary page by URL.

    Example::

        import pyerowid
        info = pyerowid.parse_substance_page(
            "https://erowid.org/pharms/acetaminophen/acetaminophen.shtml")
        print(info.name, info.other_names)
    """
    return parse_page(_t(transport).get_html(url), url)


def random_experience(*, transport: Optional[Transport] = None,
                       max_id: int = MAX_EXPERIENCE_ID,
                       attempts: int = 25) -> Optional[Experience]:
    """Return a random experience report (``None`` if none hit within *attempts*)."""
    for _ in range(attempts):
        exp = get_experience(random.randint(1, max_id), transport=transport)
        if exp is not None:
            return exp
    return None


_SORT_MAP = {
    "substance": "SA",
    "date": "PDD", "recent": "PDD",
    "old": "PDA", "older": "PDA", "oldest": "PDA",
    "rating": "RA",
}

_DEFAULT_PAGE_SIZE = 100  # server default / max observed


def search_reports(search_term: str, order: str = "substance", *,
                   start: int = 0,
                   page_size: int = _DEFAULT_PAGE_SIZE,
                   transport: Optional[Transport] = None) -> List[Report]:
    """Search experience reports for *search_term* (one page).

    Args:
        order:     ``"substance"`` (default), ``"date"``/``"recent"``,
                   ``"old"``/``"older"``/``"oldest"``, ``"rating"``, or a raw
                   ``OldSort`` value.
        start:     0-based offset into the result set (pagination via the
                   server's ``Start`` parameter).
        page_size: number of results per page (server ``Max`` parameter,
                   default 100).

    Use :func:`search_all_reports` to auto-paginate the full result set.

    Example::

        import pyerowid
        for r in pyerowid.search_reports("LSD")[:5]:
            print(r.exp_id, r.name, r.substance)
    """
    params: dict = {"Str": search_term}
    if order in _SORT_MAP:
        params["OldSort"] = _SORT_MAP[order]
    elif order is not None:
        params["OldSort"] = order
    if start:
        params["Start"] = start
        params["Max"] = page_size
    html = _t(transport).get_html("/experiences/exp.cgi", **params)
    return parse_search(html)


def search_all_reports(search_term: str, order: str = "substance", *,
                       page_size: int = _DEFAULT_PAGE_SIZE,
                       max_pages: Optional[int] = None,
                       transport: Optional[Transport] = None) -> List[Report]:
    """Search experience reports for *search_term*, auto-paginating all pages.

    Fetches the first page, reads the total page count from the ``results-table``
    banner, then fetches subsequent pages until exhausted or *max_pages* is
    reached.

    Args:
        order:      Sort order (same values as :func:`search_reports`).
        page_size:  Results per page (server ``Max``); default 100.
        max_pages:  Stop after this many pages (``None`` = no cap).

    Example::

        import pyerowid
        # All LSD reports — may be thousands; use max_pages for sampling
        all_reports = pyerowid.search_all_reports("LSD", max_pages=3)
    """
    t = _t(transport)
    params: dict = {"Str": search_term}
    if order in _SORT_MAP:
        params["OldSort"] = _SORT_MAP[order]
    elif order is not None:
        params["OldSort"] = order

    # First page (no Start/Max → server uses its own default)
    html = t.get_html("/experiences/exp.cgi", **params)
    results = parse_search(html)
    total_pages = parse_search_page_count(html)

    if max_pages is not None:
        total_pages = min(total_pages, max_pages)

    # Subsequent pages
    for page_num in range(1, total_pages):
        page_params = dict(params)
        page_params["Start"] = page_num * page_size
        page_params["Max"] = page_size
        html = t.get_html("/experiences/exp.cgi", **page_params)
        results.extend(parse_search(html))

    return results


class Erowid:
    """High-level client with a configurable transport.

    Mirrors the module-level functions, but every call uses the transport you
    configure here — no environment variables required.

    Args:
        transport:            ``"requests"`` / ``"curl_cffi"`` / ``"wayback"`` /
                              ``"flaresolverr"``, or a ready :class:`Transport`.
        flaresolverr_url:     FlareSolverr base URL (e.g.
                              ``"http://localhost:8191"``); setting it
                              selects the ``flaresolverr`` transport.
        flaresolverr_timeout_ms: per-request solve budget.
        wayback:              force the Internet Archive (same as
                              ``transport="wayback"``).
        wayback_fallback:     fall back to the archive on any live failure.

    Example::

        import pyerowid
        client = pyerowid.Erowid(flaresolverr_url="http://localhost:8191")
        exp = client.get_experience(1)
    """

    def __init__(self, transport=None, *, flaresolverr_url: Optional[str] = None,
                 flaresolverr_timeout_ms: Optional[int] = None,
                 wayback: bool = False,
                 wayback_fallback: Optional[bool] = None) -> None:
        if isinstance(transport, Transport):
            self.transport = transport
        else:
            mode = "wayback" if wayback else transport
            self.transport = Transport(
                mode=mode,
                flaresolverr_url=flaresolverr_url,
                flaresolverr_timeout_ms=flaresolverr_timeout_ms,
                wayback_fallback=wayback_fallback,
            )

    def get_experience(self, exp_id: int) -> Optional[Experience]:
        return get_experience(exp_id, transport=self.transport)

    def get_categories(self) -> List[str]:
        return get_categories(transport=self.transport)

    def get_pharms(self) -> List[SubstanceListing]:
        return get_pharms(transport=self.transport)

    def get_chemicals(self) -> List[SubstanceListing]:
        return get_chemicals(transport=self.transport)

    def get_plants(self) -> List[SubstanceListing]:
        return get_plants(transport=self.transport)

    def get_herbs(self) -> List[SubstanceListing]:
        return get_herbs(transport=self.transport)

    def get_smarts(self) -> List[SubstanceListing]:
        return get_smarts(transport=self.transport)

    def get_animals(self) -> List[SubstanceListing]:
        return get_animals(transport=self.transport)

    def parse_page(self, url: str) -> SubstanceInfo:
        return parse_substance_page(url, transport=self.transport)

    def random_experience(self) -> Optional[Experience]:
        return random_experience(transport=self.transport)

    def search_reports(self, search_term: str, order: str = "substance") -> List[Report]:
        return search_reports(search_term, order, transport=self.transport)

    def search_all_reports(self, search_term: str, order: str = "substance",
                           max_pages: Optional[int] = None) -> List[Report]:
        return search_all_reports(search_term, order,
                                  max_pages=max_pages, transport=self.transport)
