"""Typed dataclass models for pyerowid.

Shared interface on the page-backed models:

- ``site_id`` — the canonical Erowid identifier (experience id / page slug);
- ``url`` — the canonical web page;
- ``to_dict()`` — a JSON-serialisable plain ``dict``.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

BASE = "https://erowid.org"


@dataclass
class DosageEntry:
    """One row of an experience report's dose chart."""

    time: str = ""
    amount: str = ""
    method: str = ""
    substance: str = ""
    form: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class Experience:
    """A full experience report (``experiences/exp.php?ID=``).

    Example::

        import pyerowid
        exp = pyerowid.get_experience(1)
        print(exp.name, exp.substance, exp.year)
        print(exp.text[:200])
    """

    exp_id: int
    url: str
    name: str = ""
    author: str = ""
    substance: str = ""
    text: str = ""
    year: str = ""
    gender: str = ""
    age: str = ""
    date: str = ""
    dosage: List[DosageEntry] = field(default_factory=list)

    @property
    def site_id(self) -> str:
        return str(self.exp_id)

    def to_dict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        d["site_id"] = self.site_id
        return d


@dataclass
class Report:
    """A lightweight experience report stub from a search/listing result."""

    exp_id: int
    url: str
    name: str = ""
    author: str = ""
    substance: str = ""
    date: str = ""

    @property
    def site_id(self) -> str:
        return str(self.exp_id)

    def to_dict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        d["site_id"] = self.site_id
        return d


@dataclass
class SubstanceListing:
    """A substance row as it appears in a category index (``/pharms/`` etc.)."""

    name: str
    url: str
    other_names: str = ""
    effects: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class SubstanceInfo:
    """A substance vault summary page (a ``*.shtml`` topic card).

    Example::

        import pyerowid
        info = pyerowid.parse_page("https://erowid.org/pharms/acetaminophen/acetaminophen.shtml")
        print(info.name, info.other_names)
        print(info.description[:200])
    """

    name: str
    url: str
    picture: str = ""
    other_names: List[str] = field(default_factory=list)
    description: str = ""
    info: Dict[str, str] = field(default_factory=dict)
    chem_name: Optional[str] = None
    effects: Optional[str] = None
    uses: Optional[str] = None
    family: Optional[str] = None
    genus: Optional[str] = None
    species: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)
