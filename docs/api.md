# API reference

Every fetch function takes an optional `transport` keyword
([advanced.md](advanced.md)); the high-level `Erowid` client binds one for you.

## Functions

| Function | Returns | Source |
|---|---|---|
| `get_experience(exp_id)` | `Optional[Experience]` | `experiences/exp.php?ID=` |
| `search_reports(term, order="substance")` | `List[Report]` | `experiences/exp.cgi` |
| `random_experience()` | `Optional[Experience]` | random `exp.php` id |
| `get_categories()` | `List[str]` | `experiences/exp_list.shtml` |
| `get_pharms()` | `List[SubstanceListing]` | `/pharms/` |
| `get_chemicals()` | `List[SubstanceListing]` | `/chemicals/` |
| `get_plants()` | `List[SubstanceListing]` | `/plants/` |
| `get_herbs()` | `List[SubstanceListing]` | `/herbs/` |
| `get_smarts()` | `List[SubstanceListing]` | `/smarts/` |
| `get_animals()` | `List[SubstanceListing]` | `/animals/` |
| `parse_substance_page(url)` | `SubstanceInfo` | a vault `*.shtml` page |

`search_reports` `order`: `substance` (default), `date`/`recent`,
`old`/`older`/`oldest`, `rating`, or a raw `OldSort` value.

## The `Erowid` client

Binds a configurable transport so no environment variables are needed:

```python
import pyerowid
client = pyerowid.Erowid(flaresolverr_url="http://192.168.1.116:8191")
exp = client.get_experience(1)
client.search_reports("LSD")
client.get_pharms()
```

It mirrors every module-level function as a method.

## Models

### `Experience`
`exp_id`, `url`, `name`, `author`, `substance`, `text`, `year`, `gender`,
`age`, `date`, `dosage: List[DosageEntry]`. `site_id` → `str(exp_id)`;
`to_dict()`.

### `DosageEntry`
`time`, `amount`, `method`, `substance`, `form`.

### `Report` (search/listing stub)
`exp_id`, `url`, `name`, `author`, `substance`, `date`. `site_id`; `to_dict()`.

### `SubstanceListing` (vault index row)
`name`, `url`, `other_names`, `effects`.

### `SubstanceInfo` (vault summary page)
`name`, `url`, `picture`, `other_names: List[str]`, `description`,
`info: Dict[str, str]` (linked sub-pages), plus the kind-specific
`chem_name` / `effects` (chemicals, pharms, smarts) or `family` / `genus` /
`species` / `uses` (plants, herbs, animals).

## Errors

| Situation | What happens |
|---|---|
| Out-of-range / deleted experience id | `get_experience` returns `None` |
| Bad transport mode | `ValueError` |
| Network / non-2xx | underlying HTTP error propagates |

## Parsing offline

The parsers in `pyerowid.parse` take a raw HTML string and need no network —
handy for testing or feeding pre-fetched HTML:

```python
from pyerowid.parse import parse_experience, parse_search, parse_page
exp = parse_experience(open("exp.html").read(), 1)
```
