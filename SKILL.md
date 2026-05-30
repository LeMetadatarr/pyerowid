---
name: pyerowid
description: Search Erowid experience reports and substance vaults to surface harm-reduction information aloud for blind and voice-only users who cannot navigate the website.
---
# pyerowid — Erowid for agents

## When to use

Use this skill when a user asks to:
- hear an experience report read aloud ("read me a report about X")
- find first-person accounts of a substance ("what do people say about Y")
- look up substance info from the Erowid vaults (effects, other names, family)
- browse or search for reports by substance, date, or keyword

This is the accessible entry point to Erowid's harm-reduction library for users who cannot use a web browser.

## Install

```bash
pip install pyerowid
```

## Core operations

### `get_experience(exp_id: int) -> Experience | None`

Fetch a single experience report by its numeric Erowid ID.

```python
import pyerowid
exp = pyerowid.get_experience(1)
print(exp.name, "—", exp.substance, "—", exp.year)
print(exp.text[:400])
```

Returned fields: `exp_id`, `url`, `name`, `author`, `substance`, `text`, `year`, `gender`, `age`, `date`, `dosage` (list of `DosageEntry`: `time`, `amount`, `method`, `substance`, `form`).

---

### `search_reports(search_term, order="substance") -> list[Report]`

Search for experience reports matching a keyword (one page, up to 100 results).

```python
for r in pyerowid.search_reports("LSD", order="recent")[:5]:
    print(r.exp_id, r.name, r.substance, r.date)
```

`order` values: `"substance"` (default), `"date"`/`"recent"`, `"old"`/`"oldest"`, `"rating"`.
Returned fields per `Report`: `exp_id`, `url`, `name`, `author`, `substance`, `date`.

---

### `search_all_reports(search_term, order="substance") -> list[Report]`

Auto-paginate across all result pages; use for exhaustive lookups.

```python
all_reports = pyerowid.search_all_reports("psilocybin")
print(f"{len(all_reports)} reports found")
```

---

### `get_pharms() -> list[SubstanceListing]`

List the pharmaceutical vault index.

```python
for s in pyerowid.get_pharms()[:5]:
    print(s.name, "—", s.effects)
```

---

### `get_chemicals() -> list[SubstanceListing]`

List the synthetic/research-chemical vault index.

```python
for s in pyerowid.get_chemicals()[:5]:
    print(s.name, s.other_names)
```

---

### `get_plants() -> list[SubstanceListing]`

List the plant vault index.

---

### `get_herbs() -> list[SubstanceListing]`

List the herb vault index.

---

### `get_smarts() -> list[SubstanceListing]`

List the smart-products vault index.

---

### `get_animals() -> list[SubstanceListing]`

List the animal-derived substances vault index.

All vault functions return `SubstanceListing` objects with fields: `name`, `url`, `other_names`, `effects`.

---

### `get_categories() -> list[str]`

Return the list of substance category names used in the experience-report index.

```python
print(pyerowid.get_categories())
```

---

### `parse_substance_page(url: str) -> SubstanceInfo`

Fetch and parse a substance vault summary page by its full URL.

```python
info = pyerowid.parse_substance_page(
    "https://erowid.org/pharms/acetaminophen/acetaminophen.shtml")
print(info.name, info.other_names, info.description[:200])
```

Returned fields: `name`, `url`, `picture`, `other_names`, `description`, `info` (dict), `chem_name`, `effects`, `uses`, `family`, `genus`, `species`.

---

### `random_experience() -> Experience | None`

Return a random experience report; useful for discovery or demo.

```python
exp = pyerowid.random_experience()
if exp:
    print(exp.name, exp.substance, exp.year)
```

## Access notes

The client scrapes Erowid HTML directly. When the live site is blocked or unavailable, the transport layer transparently retries through the Internet Archive (Wayback Machine), so substance catalogs and reports stay readable even during outages.

## Speaking the results (accessibility)

- Introduce a report: "This is a report titled *{name}*, about {substance}, submitted in {year}."
- Offer to continue: "Shall I read the full account, or just the dosage summary?"
- Support discovery: "I found {n} reports for {term}. I can read the most recent, highest-rated, or pick one at random."
- Stay factual and harm-reduction framed: relay the author's first-person account without editorialising; note dose and method when present.
