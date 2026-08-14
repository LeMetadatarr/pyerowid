"""HF-publishable dataset builders for erowid.org.

Two configs, each a stream of flat JSON rows:

- **experiences** — first-person reports (exp_id, substance, dose, year, text, …).
- **substances**  — vault summary pages (name, other_names, chem_name, effects, …).

Rows are emitted lazily and written as JSONL (one JSON object per line). The
crawler is **resumable**: at startup it scans the destination file for IDs
already collected and skips them, so a crawl can be stopped and restarted
without re-fetching anything. Erowid has 100k+ experience ids — a full crawl is
a homelab job; see ``docs/dataset.md``.

Run::

    python -m pyerowid.dataset experiences --out erowid-experiences.jsonl
    python -m pyerowid.dataset substances  --out erowid-substances.jsonl
    python -m pyerowid.dataset all         --out erowid_dataset/
"""
from __future__ import annotations

import argparse
import json
import os
import time
from typing import Dict, Iterator, List, Optional, Set

from pyerowid._transport import Transport, default_transport
from pyerowid.reports import (
    _CATEGORY_BASES,
    MAX_EXPERIENCE_ID,
    get_experience,
    parse_substance_page,
)
from pyerowid.types import Experience, SubstanceInfo, SubstanceListing

CONFIGS = ("experiences", "substances")


# ---------------------------------------------------------------------------
# Row serialisers
# ---------------------------------------------------------------------------

def _exp_row(exp: Experience) -> dict:
    return {
        "exp_id": exp.exp_id,
        "url": exp.url,
        "name": exp.name,
        "author": exp.author,
        "substance": exp.substance,
        "text": exp.text,
        "year": exp.year,
        "gender": exp.gender,
        "age": exp.age,
        "date": exp.date,
        "dosage": [
            {
                "time": d.time,
                "amount": d.amount,
                "method": d.method,
                "substance": d.substance,
                "form": d.form,
            }
            for d in exp.dosage
        ],
    }


def _substance_row(info: SubstanceInfo) -> dict:
    return {
        "name": info.name,
        "url": info.url,
        "picture": info.picture,
        "other_names": info.other_names,
        "description": info.description,
        "info": info.info,
        "chem_name": info.chem_name,
        "effects": info.effects,
        "uses": info.uses,
        "family": info.family,
        "genus": info.genus,
        "species": info.species,
    }


# ---------------------------------------------------------------------------
# Resumability helpers
# ---------------------------------------------------------------------------

def _read_done_exp_ids(path: str) -> Set[int]:
    """Return the set of exp_ids already written to *path* (empty if absent)."""
    done: Set[int] = set()
    if not os.path.exists(path):
        return done
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                done.add(json.loads(line)["exp_id"])
            except Exception:
                pass
    return done


def _read_done_substance_names(path: str) -> Set[str]:
    """Return substance names already written to *path* (empty if absent)."""
    done: Set[str] = set()
    if not os.path.exists(path):
        return done
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                done.add(json.loads(line)["name"])
            except Exception:
                pass
    return done


# ---------------------------------------------------------------------------
# Row iterators (lazy, resumable)
# ---------------------------------------------------------------------------

def iter_experiences(
    *,
    transport: Optional[Transport] = None,
    delay: float = 2.0,
    done: Optional[Set[int]] = None,
    verbose: bool = True,
) -> Iterator[dict]:
    """Yield experience rows for IDs 1..MAX_EXPERIENCE_ID, skipping *done* ids."""
    t = transport or default_transport()
    done = done or set()
    todo = [i for i in range(1, MAX_EXPERIENCE_ID + 1) if i not in done]
    if verbose:
        print(f"experiences: {len(todo)} ids to fetch (skipping {len(done)} already done)")
    for exp_id in todo:
        exp = get_experience(exp_id, transport=t)
        time.sleep(delay)
        if exp is None:
            continue
        yield _exp_row(exp)


def iter_substances(
    *,
    transport: Optional[Transport] = None,
    delay: float = 2.0,
    done: Optional[Set[str]] = None,
    verbose: bool = True,
) -> Iterator[dict]:
    """Yield substance rows for all vault categories, skipping *done* names."""
    from pyerowid.reports import _extract_list

    t = transport or default_transport()
    done = done or set()
    for category in sorted(_CATEGORY_BASES):
        if verbose:
            print(f"substances: fetching category '{category}'")
        try:
            listings: List[SubstanceListing] = _extract_list(category, transport=t)
        except Exception as e:
            if verbose:
                print(f"  category '{category}' index failed: {e}")
            continue
        for listing in listings:
            if listing.name in done:
                if verbose:
                    print(f"  skip {listing.name} (already done)")
                continue
            try:
                info: SubstanceInfo = parse_substance_page(listing.url, transport=t)
            except Exception as e:
                if verbose:
                    print(f"  err {listing.name}: {e}")
                continue
            time.sleep(delay)
            done.add(info.name)
            yield _substance_row(info)


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

def export_jsonl(
    config: str,
    path: str,
    *,
    transport: Optional[Transport] = None,
    delay: float = 2.0,
    limit: Optional[int] = None,
    verbose: bool = True,
) -> int:
    """Crawl *config* and append rows to the JSONL file at *path*.

    Resumable: reads already-collected rows from *path* before crawling.
    Returns the number of **new** rows written this run.
    """
    if config not in CONFIGS:
        raise ValueError(f"unknown config {config!r}; expected one of {CONFIGS}")

    if config == "experiences":
        done_ids = _read_done_exp_ids(path)
        rows = iter_experiences(transport=transport, delay=delay,
                                done=done_ids, verbose=verbose)
    else:
        done_names = _read_done_substance_names(path)
        rows = iter_substances(transport=transport, delay=delay,
                               done=done_names, verbose=verbose)

    written = 0
    with open(path, "a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
            if verbose and written % 100 == 0:
                print(f"  {config}: {written} new rows written")
            if limit is not None and written >= limit:
                break

    if verbose:
        print(f"wrote {written} new {config} rows -> {path}")
    return written


def export_all(out_dir: str, *, transport: Optional[Transport] = None,
               delay: float = 2.0, verbose: bool = True) -> Dict[str, int]:
    """Export every config into ``{out_dir}/<config>.jsonl``. Returns counts."""
    os.makedirs(out_dir, exist_ok=True)
    counts: Dict[str, int] = {}
    for config in CONFIGS:
        path = os.path.join(out_dir, f"erowid-{config}.jsonl")
        counts[config] = export_jsonl(config, path, transport=transport,
                                      delay=delay, verbose=verbose)
    return counts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build Erowid HF datasets (experiences / substances).")
    parser.add_argument("config", choices=(*CONFIGS, "all"),
                        help="dataset config to export")
    parser.add_argument("--out", help="output .jsonl file (or dir for 'all')")
    parser.add_argument("--limit", type=int, default=None,
                        help="cap on rows (validation / partial run)")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="seconds between live fetches (default: 2.0)")
    parser.add_argument("--transport",
                        choices=["requests", "curl_cffi", "wayback", "flaresolverr"],
                        help="override the HTTP transport mode")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    transport = (
        Transport(mode=args.transport) if args.transport else default_transport()
    )
    verbose = not args.quiet

    if args.config == "all":
        out = args.out or "erowid_dataset"
        counts = export_all(out, transport=transport, delay=args.delay,
                            verbose=verbose)
        if verbose:
            print("done:", counts)
        return 0

    out = args.out or f"erowid-{args.config}.jsonl"
    export_jsonl(args.config, out, transport=transport, delay=args.delay,
                 limit=args.limit, verbose=verbose)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
