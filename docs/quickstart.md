# Quickstart — zero to hero

From `pip install` to experience reports and substance vault pages.

## 1. Install

```bash
pip install pyerowid[stealth]
```

The `stealth` extra pulls in `curl_cffi` Chrome TLS impersonation, used by the
transport for resilient fetches. See [advanced.md](advanced.md) for the
transport modes.

## 2. The mental model

Erowid has two things this client reads:

```
Experience (a first-person report)   ── exp.php?ID=
Substance  (a vault summary page)    ── /pharms/ /chemicals/ /plants/ …
```

- An **`Experience`** is a full report: title, author, substance, year,
  demographics, a dose chart (`DosageEntry` rows) and the body text.
- A **`Report`** is the lightweight stub returned by search/listings.
- A **`SubstanceListing`** is a row in a vault category index.
- A **`SubstanceInfo`** is a parsed substance summary page.

## 3. A single experience report

```python
import pyerowid

exp = pyerowid.get_experience(1)
print(exp.name, "—", exp.substance, "—", exp.year)
for d in exp.dosage:
    print(d.time, d.amount, d.method, d.substance)
print(exp.text[:300])
```

Out-of-range or deleted ids return `None`.

## 4. Search reports

```python
for r in pyerowid.search_reports("LSD", order="recent")[:10]:
    print(r.exp_id, r.substance, r.name)
```

`order` is one of `substance` (default), `date`/`recent`, `old`/`oldest`,
`rating`.

## 5. Browse the substance vaults

```python
print(pyerowid.get_categories())
for s in pyerowid.get_pharms()[:5]:
    print(s.name, "—", s.effects)
```

Vault helpers: `get_pharms`, `get_chemicals`, `get_plants`, `get_herbs`,
`get_smarts`, `get_animals`.

## 6. A substance summary page

```python
info = pyerowid.parse_substance_page(
    "https://erowid.org/pharms/acetaminophen/acetaminophen.shtml")
print(info.name, info.other_names, info.chem_name)
print(info.description[:300])
```

## 7. Serialise

```python
import json
print(json.dumps(exp.to_dict(), indent=2, ensure_ascii=False))
```

## Next steps

- [api.md](api.md) — every function and model field
- [advanced.md](advanced.md) — transport modes, politeness, errors
- [dataset.md](dataset.md) — the markdown corpus dumper and the ML roadmap
