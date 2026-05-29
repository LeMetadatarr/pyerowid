"""pyerowid — typed Python client for Erowid (erowid.org) + a markdown corpus dumper.

Erowid is a reference library of psychoactive-substance information and
first-person experience reports, maintained as a harm-reduction resource. This
package scrapes its HTML behind clean dataclasses: read experience reports,
browse the substance vaults (pharms / chemicals / plants / herbs / smarts /
animals), search reports, and dump a markdown corpus for downstream NLP.

Quick start::

    import pyerowid

    # A single experience report
    exp = pyerowid.get_experience(1)
    print(exp.name, "—", exp.substance, "—", exp.year)
    print(exp.text[:200])

    # Search reports
    for r in pyerowid.search_reports("LSD")[:5]:
        print(r.exp_id, r.name, r.substance)

    # Browse a substance vault
    for s in pyerowid.get_pharms()[:5]:
        print(s.name, "—", s.effects)

    # A substance summary page
    info = pyerowid.parse_substance_page(
        "https://erowid.org/pharms/acetaminophen/acetaminophen.shtml")
    print(info.name, info.other_names)

    # A random report
    print(pyerowid.random_experience().name)
"""
from pyerowid.types import (
    DosageEntry,
    Experience,
    Report,
    SubstanceInfo,
    SubstanceListing,
)
from pyerowid.reports import (
    Erowid,
    get_animals,
    get_categories,
    get_chemicals,
    get_experience,
    get_herbs,
    get_pharms,
    get_plants,
    get_smarts,
    parse_substance_page,
    random_experience,
    search_reports,
)
from pyerowid._transport import Transport
from pyerowid.version import __version__

__all__ = [
    "DosageEntry",
    "Experience",
    "Report",
    "SubstanceInfo",
    "SubstanceListing",
    "Erowid",
    "Transport",
    "get_animals",
    "get_categories",
    "get_chemicals",
    "get_experience",
    "get_herbs",
    "get_pharms",
    "get_plants",
    "get_smarts",
    "parse_substance_page",
    "random_experience",
    "search_reports",
    "__version__",
]
