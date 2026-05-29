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


def search_reports(search_term: str, order: str = "substance", *,
                   transport: Optional[Transport] = None) -> List[Report]:
    """Search experience reports for *search_term*.

    Args:
        order: ``"substance"`` (default), ``"date"``/``"recent"``,
               ``"old"``/``"older"``/``"oldest"``, ``"rating"``, or a raw
               ``OldSort`` value.

    Example::

        import pyerowid
        for r in pyerowid.search_reports("LSD")[:5]:
            print(r.exp_id, r.name, r.substance)
    """
    params = {"Str": search_term}
    sort_map = {
        "substance": "SA",
        "date": "PDD", "recent": "PDD",
        "old": "PDA", "older": "PDA", "oldest": "PDA",
        "rating": "RA",
    }
    if order in sort_map:
        params["OldSort"] = sort_map[order]
    elif order is not None:
        params["OldSort"] = order
    html = _t(transport).get_html("/experiences/exp.cgi", **params)
    return parse_search(html)


class Erowid:
    """High-level client with a configurable transport.

    Mirrors the module-level functions, but every call uses the transport you
    configure here — no environment variables required.

    Args:
        transport:            ``"requests"`` / ``"curl_cffi"`` / ``"wayback"`` /
                              ``"flaresolverr"``, or a ready :class:`Transport`.
        flaresolverr_url:     FlareSolverr base URL (e.g.
                              ``"http://192.168.1.116:8191"``); setting it
                              selects the ``flaresolverr`` transport.
        flaresolverr_timeout_ms: per-request solve budget.
        wayback:              force the Internet Archive (same as
                              ``transport="wayback"``).
        wayback_fallback:     fall back to the archive on any live failure.

    Example::

        import pyerowid
        client = pyerowid.Erowid(flaresolverr_url="http://192.168.1.116:8191")
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
