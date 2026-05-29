# pyerowid

Typed Python client for [Erowid](https://erowid.org) — the harm-reduction
reference library of psychoactive-substance information and first-person
experience reports — plus a markdown corpus dumper for downstream NLP.

It scrapes the site's HTML behind clean dataclasses: read experience reports,
search them, browse the substance vaults (pharms / chemicals / plants / herbs /
smarts / animals), parse substance summary pages, and dump a resumable markdown
corpus.

> Erowid is a small, donation-funded nonprofit. This client is for
> **harm-reduction and research** use — be a polite guest: reuse a session and
> throttle your requests.

## Install

```bash
pip install pyerowid
pip install pyerowid[stealth]   # adds curl-cffi TLS impersonation (recommended)
pip install pyerowid[test]      # adds pytest
```

All HTTP routes through the org transport
[`unblock_requests`](../../utils/unblock_requests) (a drop-in
`requests.Session` subclass). Pick the fetch mode with `PYEROWID_TRANSPORT`
(`curl_cffi` default, `requests`, `wayback`, `flaresolverr`) — see
[docs/advanced.md](docs/advanced.md).

## 30-second tour

```python
import pyerowid

# A single experience report
exp = pyerowid.get_experience(1)
print(exp.name, "—", exp.substance, "—", exp.year)
for d in exp.dosage:
    print(d.time, d.amount, d.method, d.substance)
print(exp.text[:300])

# Search reports
for r in pyerowid.search_reports("LSD", order="recent")[:5]:
    print(r.exp_id, r.substance, r.name)

# Browse a substance vault
for s in pyerowid.get_pharms()[:5]:
    print(s.name, "—", s.effects)

# A substance summary page
info = pyerowid.parse_substance_page(
    "https://erowid.org/pharms/acetaminophen/acetaminophen.shtml")
print(info.name, info.other_names, info.chem_name)
```

## What you can fetch

| Function | Returns | Source |
|---|---|---|
| `get_experience(id)` | `Optional[Experience]` | `exp.php?ID=` |
| `search_reports("LSD")` | `List[Report]` | `exp.cgi` |
| `random_experience()` | `Optional[Experience]` | random id |
| `get_categories()` | `List[str]` | `exp_list.shtml` |
| `get_pharms()` / `get_chemicals()` / `get_plants()` / `get_herbs()` / `get_smarts()` / `get_animals()` | `List[SubstanceListing]` | the vault indexes |
| `parse_substance_page(url)` | `SubstanceInfo` | a vault `*.shtml` page |

The high-level `pyerowid.Erowid` client mirrors these as methods over a
configured transport.

## Markdown corpus dumper

`pyerowid.dataset` writes one markdown file per item (YAML front-matter + body),
resumable and polite:

```bash
python -m pyerowid.dataset --out corpus --search LSD --limit 10
python -m pyerowid.dataset --out corpus --substances pharms --max-substances 5
```

A full crawl (100k+ experience ids) is a **homelab job** — validate on a small
sample first. See [docs/dataset.md](docs/dataset.md) for the corpus format, the
ML task roadmap (substance NER, classification, RAG, summarisation), and the
Hugging Face publishing / legality notes.

## Documentation

Start with **[docs/quickstart.md](docs/quickstart.md)**, then:

- [docs/api.md](docs/api.md) — every function and model field
- [docs/advanced.md](docs/advanced.md) — transport modes, politeness, errors
- [docs/dataset.md](docs/dataset.md) — the corpus dumper and ML/dataset roadmap

Runnable, numbered scripts live in [examples/](examples/).
