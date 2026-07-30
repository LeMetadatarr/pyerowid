"""Pure HTML → model parsers for erowid.org.

These functions take raw HTML strings and return typed models, with no network
access — so they can be unit-tested against saved fixtures. The fetching layer
(:mod:`pyerowid.reports`) wires them to HTTP.

Verified against the live markup:

- **Experience** (``experiences/exp.php?ID=``): a ``div.title`` / ``div.author``
  / ``div.substance`` header, a ``table.footdata`` carrying year / gender / age /
  publication date, a ``table.dosechart`` of dose rows, and the report body
  between ``<!-- Start Body -->`` / ``<!-- End Body -->`` comments.
- **Category index** (``/pharms/`` etc.): a ``table.topic-chart-surround`` of
  ``tr.topic-surround`` rows — (name+link, common names, effects).
- **Search** (``experiences/exp.cgi``): a ``table.exp-list-table`` of
  ``tr.exp-list-row`` rows linking to ``exp.php?ID=``.
- **Substance vault** (``*.shtml`` topic card): ``div.title-section`` name plus
  ``div.sum-*`` summary blocks.
"""
from __future__ import annotations

import re
from typing import List, Optional

from bs4 import BeautifulSoup

from pyerowid.types import (
    DosageEntry,
    Experience,
    Report,
    SubstanceInfo,
    SubstanceListing,
)

_EXP_BASE = "https://erowid.org/experiences/exp.php"
_ID_RE = re.compile(r"ID=(\d+)", re.I)


def extract_experience_text(html: str) -> str:
    """Return the report body between the ``Start Body`` / ``End Body`` comments."""
    begin_delimiter = "<!-- Start Body -->"
    try:
        begin = html.index(begin_delimiter) + len(begin_delimiter)
        end = html.index("<!-- End Body -->")
    except ValueError:
        return ""
    body = html[begin:end].strip()
    return (body.replace("<BR>", "\n").replace("<br>", "\n")
            .replace("<br/>", "\n").replace("\n\n", " ").strip())


def parse_experience(html: str, exp_id: int) -> Optional[Experience]:
    """Parse an ``exp.php?ID=`` page into an :class:`Experience`.

    Returns ``None`` when the page carries no report (deleted / out-of-range id).
    """
    url = f"{_EXP_BASE}?ID={exp_id}"
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("div", {"class": "title"})
    if not title or not title.get_text().strip():
        return None

    exp = Experience(exp_id=int(exp_id), url=url)
    exp.name = title.get_text().strip()
    exp.text = extract_experience_text(html)

    author = soup.find("div", {"class": "author"})
    if author:
        exp.author = author.get_text().strip()
    substance = soup.find("div", {"class": "substance"})
    if substance:
        exp.substance = substance.get_text().strip().lower().replace("/", ", ")

    footdata = soup.find("table", {"class": "footdata"})
    if footdata:
        lines = footdata.get_text().strip().lower().split("\n")
        if len(lines) > 0:
            exp.year = lines[0].split("expid:")[0].replace("exp year: ", "").strip()
        if len(lines) > 1:
            exp.gender = lines[1].replace("gender: ", "").strip()
        if len(lines) > 2:
            exp.age = lines[2].replace("age at time of experience: ", "").strip()
        if len(lines) > 3:
            exp.date = lines[3].replace("published: ", "").split("views:")[0].strip()

    dosage_table = soup.find("table", {"class": "dosechart"})
    if dosage_table:
        times = dosage_table.find_all("td", {"align": "right"})
        amount = dosage_table.find_all("td", {"class": "dosechart-amount"})
        method = dosage_table.find_all("td", {"class": "dosechart-method"})
        substance_cells = dosage_table.find_all("td", {"class": "dosechart-substance"})
        form = dosage_table.find_all("td", {"class": "dosechart-form"})
        for i in range(len(times)):
            exp.dosage.append(DosageEntry(
                time=times[i].get_text().lower().replace("dose:", "").strip(),
                amount=amount[i].get_text().strip().lower() if i < len(amount) else "",
                method=method[i].get_text().strip().lower() if i < len(method) else "",
                substance=substance_cells[i].get_text().strip().lower() if i < len(substance_cells) else "",
                form=form[i].get_text().strip().lower() if i < len(form) else "",
            ))
    return exp


def parse_categories(html: str) -> List[str]:
    """Parse the experience category names from the ``exp_list`` page."""
    categories = []
    for sub in html.split("<!-- Start ")[1:]:
        categories.append(sub[:sub.find(" -->")])
    return categories


def parse_substance_list(html: str, base_url: str) -> List[SubstanceListing]:
    """Parse a category index (``/pharms/`` etc.) into :class:`SubstanceListing`."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"class": "topic-chart-surround"})
    if not table:
        return []
    rows = table.find_all("tr", {"class": "topic-surround"})[1:]
    listings: List[SubstanceListing] = []
    for cat in rows:
        name = cat.find("td", {"class": "topic-name"})
        if not name:
            continue
        link = name.find("a")
        common = cat.find("td", {"class": "topic-common"})
        desc = cat.find("td", {"class": "topic-desc"})
        listings.append(SubstanceListing(
            name=name.get_text().strip().lower(),
            url=base_url + link["href"] if link and link.get("href") else base_url,
            other_names=common.get_text().strip().lower() if common else "",
            effects=desc.get_text().strip().lower() if desc else "",
        ))
    return listings


def parse_search(html: str) -> List[Report]:
    """Parse a search-results page (``exp.cgi``) into :class:`Report` stubs.

    Handles both classed (``tr.exp-list-row``) and unclassed ``<tr>`` rows —
    the live site emits rows with no class; the selector falls back to any row
    inside ``table.exp-list-table`` that carries an ``ID=`` link.
    """
    base_url = "https://erowid.org/experiences/"
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"class": "exp-list-table"})
    if not table:
        return []
    reports: List[Report] = []
    # Prefer explicit class; fall back to any row with an ID link.
    candidate_rows = table.find_all("tr", {"class": "exp-list-row"})
    if not candidate_rows:
        candidate_rows = [r for r in table.find_all("tr") if r.find("a", href=_ID_RE)]
    for r in candidate_rows:
        link = r.find("a", href=_ID_RE)
        if not link:
            continue
        m = _ID_RE.search(link.get("href", ""))
        if not m:
            continue
        # the meaningful cells are name, author, substance, date (last four)
        cells = [td.get_text(strip=True) for td in r.find_all("td")]
        tail = cells[-4:] if len(cells) >= 4 else cells
        name, author, substance, date = (tail + ["", "", "", ""])[:4]
        reports.append(Report(
            exp_id=int(m.group(1)),
            url=base_url + link["href"],
            name=name,
            author=author,
            substance=substance,
            date=date,
        ))
    return reports


def parse_search_page_count(html: str) -> int:
    """Return the total number of paginated pages from a search results page.

    Reads the ``table.results-table`` banner (e.g. *"Page 1 of 3 / 232 reports
    returned"*) and returns the page count; returns ``1`` when the banner is
    absent (single-page result or unknown).
    """
    soup = BeautifulSoup(html, "html.parser")
    tbl = soup.find("table", {"class": "results-table"})
    if not tbl:
        return 1
    m = re.search(r"page\s+\d+\s+of\s+(\d+)", tbl.get_text(), re.I)
    return int(m.group(1)) if m else 1


def parse_page(html: str, url: str) -> SubstanceInfo:
    """Parse a substance vault summary page into a :class:`SubstanceInfo`."""
    base_url = url
    if ".shtml" in base_url:
        base_url = "/".join(base_url.split("/")[:-1]) + "/"
    soup = BeautifulSoup(html, "html.parser")

    title = soup.find("div", {"class": "title-section"})
    info = SubstanceInfo(
        name=title.get_text().strip().lower() if title else "",
        url=base_url,
    )

    image = soup.find("div", {"class": "summary-card-topic-image"})
    picture = image.find("img") if image else None
    info.picture = base_url + picture["src"] if picture and picture.get("src") else ""

    common = soup.find("div", {"class": "sum-common-name"})
    if common:
        info.other_names = [n.strip().lower() for n in common.get_text().split(";")]
    desc = soup.find("div", {"class": "sum-description"})
    if desc:
        info.description = desc.get_text()

    icons = soup.find("div", {"class": "summary-card-icon-surround"})
    if icons:
        for a in icons.find_all("a"):
            img = a.find("img")
            if a.get("href") and img and img.get("alt"):
                info.info[img["alt"].strip().lower()] = base_url + a["href"]

    def _txt(cls: str) -> Optional[str]:
        el = soup.find("div", {"class": cls})
        return el.get_text() if el else None

    if "/chem" in url or "/pharms" in url or "/smarts" in url:
        info.chem_name = _txt("sum-chem-name")
        info.effects = _txt("sum-effects")
    elif "/animals" in url or "/plants" in url or "/herbs" in url:
        rows = soup.find_all("div", {"class": "fgs-row"})
        if len(rows) > 0 and rows[0].find("div", {"class": "family"}):
            info.family = rows[0].find("div", {"class": "family"}).get_text()
        if len(rows) > 1 and rows[1].find("div", {"class": "genus"}):
            info.genus = rows[1].find("div", {"class": "genus"}).get_text()
        if len(rows) > 2 and rows[2].find("div", {"class": "species"}):
            info.species = rows[2].find("div", {"class": "species"}).get_text()
        if "/herbs" in url:
            info.uses = _txt("sum-uses")
        else:
            info.effects = _txt("sum-effects")

    return info
