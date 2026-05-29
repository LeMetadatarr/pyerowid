# Datasets, the markdown corpus dumper, and the ML roadmap

This client produces a **markdown corpus**: one file per item, with YAML
front-matter (metadata) and a body. That format is friction-free for RAG
ingestion, fine-tuning pipelines, and human review alike.

## The dumper

`pyerowid.dataset` crawls Erowid and writes markdown into an output folder:

```
corpus/
  experiences/<exp_id>.md     # title, author, substance, dose, year, body
  substances/<slug>.md        # vault summary: names, chem name, effects, description
```

It is **resumable** (an existing file is skipped, so a crawl can be stopped and
resumed) and **polite** (one shared `Transport`/session; a `delay` between
fetches).

### Library

```python
import pyerowid
from pyerowid import dataset

dataset.dump_experiences("corpus", [1, 2, 14], delay=1.0)
dataset.dump_search("corpus", "LSD", limit=20, order="recent", delay=1.0)
dataset.dump_substances("corpus", pyerowid.get_pharms(), delay=1.0)
```

### CLI

```bash
python -m pyerowid.dataset --out corpus --experiences 5          # ids 1..5
python -m pyerowid.dataset --out corpus --ids 1,2,14
python -m pyerowid.dataset --out corpus --search LSD --limit 10
python -m pyerowid.dataset --out corpus --substances pharms --max-substances 5
```

(Installed as the `pyerowid-dump` console script too.)

> **Bulk crawl is a homelab job.** Erowid has 100k+ experience ids and the
> vaults add thousands of substance pages. Validate locally on a small sample
> (the defaults are tiny on purpose), then run the full crawl on the homelab box
> with a generous `--delay`, resuming as needed — never hammer the site from a
> dev loop.

## What datasets this client can produce

| Dataset | Source | Shape | Headline fields |
|---|---|---|---|
| **Experience reports** | `exp.php` / search | one md/report | `text` (long free-text), `substance`, `year`, `dosage`, demographics |
| **Substance vault** | `/pharms/` … vault pages | one md/substance | `name`, `other_names`, `chem_name`, `effects`/`uses`, `description` |
| **Dose records** | dose charts inside reports | tabular rows | `substance`, `amount`, `method`, `time`, `form` |

The experience corpus is the flagship: tens of thousands of long, structured,
first-person narratives each tagged with substance, dose and year.

## ML tasks these serve

- **Substance NER** — the vault `name`/`other_names` (including slang and brand
  names) are a ready gazetteer for training/evaluating a substance + dose +
  route entity tagger over free text.
- **Experience classification** — substance, route of administration, year, and
  (where present) demographic fields are labels for multi-label classification
  of report text.
- **Dose extraction** — the dose charts give aligned (text ↔ structured dose)
  pairs for an amount/route/timing extractor.
- **Retrieval / RAG** — the markdown corpus is built for chunk-and-embed; it is
  the substrate for **a harm-reduction assistant** that answers grounded in
  real reports + substance facts rather than model priors.
- **Summarisation** — long reports → short, safety-oriented summaries (onset,
  peak, comedown, adverse effects).

## Publishing on Hugging Face — legality and framing

Erowid content is **sensitive** and the experience reports are
**user-contributed under Erowid's terms**. Treat publication conservatively:

- **Do not** mirror the raw experience-report corpus to a public HF dataset.
  The reports are Erowid's curated, contributor-submitted material; redistributing
  them in bulk is a content-licensing and ToS question, and the narratives can
  carry personal detail. Keep that corpus **private / internal** — it feeds our
  own RAG assistant, it is not a redistribution product.
- **Publishable, with care:** *derived, non-substitutive* artifacts — e.g. a
  substance-name/slang gazetteer (mostly factual lists), or aggregate dose
  statistics (counts/distributions, no report text). Even these should ship with
  clear provenance/attribution to Erowid and a link back.
- **Framing is mandatory:** any release is **harm-reduction**, not
  how-to. Include a prominent disclaimer, attribution to Erowid, the
  non-medical-advice caveat, and a contact for takedown. When in doubt, ask
  Erowid directly — they are reachable and reasonable about research use.

The default posture: **keep the report corpus internal**, publish only
clearly-derived factual aggregates, and always with harm-reduction framing and
attribution.
