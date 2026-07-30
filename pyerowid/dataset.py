"""Markdown corpus dumper for erowid.org.

Crawls Erowid and writes **one markdown file per item** into an output folder:
YAML front-matter with metadata, then the body text. Two item kinds:

- **experiences** — first-person reports (substance / dose / year + text);
- **substances**  — vault summary pages (pharms / chemicals / plants / …).

The dump is **resumable** (already-written files are skipped) and **polite**
(one shared :class:`~pyerowid._transport.Transport`/session, a modest delay
between requests). Erowid has 100k+ experience ids — a full crawl is a homelab
job; see ``docs/dataset.md``. The CLI defaults to a tiny sample.

Run::

    python -m pyerowid.dataset --out corpus --experiences 5
    python -m pyerowid.dataset --out corpus --search LSD --limit 10
    python -m pyerowid.dataset --out corpus --substances pharms
"""
from __future__ import annotations

import argparse
import os
import re
import time
from typing import Any, Dict, Iterable, List, Optional

from pyerowid._transport import Transport, default_transport
from pyerowid.reports import (
    _CATEGORY_BASES,
    get_experience,
    parse_substance_page,
    search_all_reports,
    search_reports,
)
from pyerowid.types import Experience, SubstanceInfo, SubstanceListing

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(text: str) -> str:
    return _SLUG_RE.sub("-", (text or "").strip().lower()).strip("-") or "item"


def _yaml_scalar(value: Any) -> str:
    """Render a scalar for YAML front-matter, quoting when needed."""
    s = "" if value is None else str(value)
    if s == "" or re.search(r"[:#\-\[\]{}&*!|>'\"%@`,]", s) or s.strip() != s:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def _front_matter(meta: Dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in meta.items():
        if isinstance(value, (list, tuple)):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {_yaml_scalar(item)}")
        else:
            lines.append(f"{key}: {_yaml_scalar(value)}")
    lines.append("---")
    return "\n".join(lines)


def experience_markdown(exp: Experience) -> str:
    """Render an :class:`Experience` as a markdown document."""
    meta = {
        "kind": "experience",
        "exp_id": exp.exp_id,
        "title": exp.name,
        "author": exp.author,
        "substance": exp.substance,
        "year": exp.year,
        "gender": exp.gender,
        "age": exp.age,
        "date": exp.date,
        "url": exp.url,
    }
    parts = [_front_matter(meta), "", f"# {exp.name}".rstrip(), ""]
    if exp.dosage:
        parts.append("## Dosage\n")
        parts.append("| Time | Amount | Method | Substance | Form |")
        parts.append("| --- | --- | --- | --- | --- |")
        for d in exp.dosage:
            parts.append(f"| {d.time} | {d.amount} | {d.method} | {d.substance} | {d.form} |")
        parts.append("")
    parts.append("## Report\n")
    parts.append(exp.text)
    parts.append("")
    return "\n".join(parts)


def substance_markdown(info: SubstanceInfo) -> str:
    """Render a :class:`SubstanceInfo` as a markdown document."""
    meta = {
        "kind": "substance",
        "name": info.name,
        "other_names": info.other_names,
        "url": info.url,
    }
    for opt in ("chem_name", "effects", "uses", "family", "genus", "species"):
        val = getattr(info, opt)
        if val:
            meta[opt] = val
    parts = [_front_matter(meta), "", f"# {info.name}".rstrip(), "", info.description, ""]
    return "\n".join(parts)


def _write_if_absent(path: str, render) -> bool:
    """Write *render()* to *path* unless it exists. Returns True if written."""
    if os.path.exists(path):
        return False
    text = render()
    if text is None:
        return False
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return True


def dump_experiences(out_dir: str, exp_ids: Iterable[int], *,
                     transport: Optional[Transport] = None,
                     delay: float = 1.0, verbose: bool = True) -> int:
    """Write one markdown file per experience id into ``{out_dir}/experiences``.

    Resumable (skips existing files) and polite (sleeps *delay* s between live
    fetches). Returns the number of files written this run.
    """
    t = transport or default_transport()
    folder = os.path.join(out_dir, "experiences")
    os.makedirs(folder, exist_ok=True)
    written = 0
    for exp_id in exp_ids:
        path = os.path.join(folder, f"{int(exp_id)}.md")
        if os.path.exists(path):
            if verbose:
                print(f"  skip exp {exp_id} (exists)")
            continue
        exp = get_experience(exp_id, transport=t)
        time.sleep(delay)
        if exp is None:
            if verbose:
                print(f"  miss exp {exp_id} (no report)")
            continue
        if _write_if_absent(path, lambda: experience_markdown(exp)):
            written += 1
            if verbose:
                print(f"  wrote exp {exp_id}: {exp.name}")
    return written


def dump_search(out_dir: str, query: str, *, limit: Optional[int] = None,
                order: str = "substance", all_pages: bool = False,
                max_pages: Optional[int] = None,
                transport: Optional[Transport] = None,
                delay: float = 1.0, verbose: bool = True) -> int:
    """Search reports for *query* and dump (up to *limit*) of them as markdown.

    Args:
        all_pages:  When ``True`` auto-paginate through all search result pages
                    (uses :func:`~pyerowid.reports.search_all_reports`).
        max_pages:  Cap pagination at this many pages (implies ``all_pages``).
                    ``None`` = no cap (use with care on large queries).
        limit:      Hard cap on the number of experience IDs to fetch after
                    search results are collected.
    """
    t = transport or default_transport()
    if all_pages or max_pages is not None:
        reports = search_all_reports(query, order, max_pages=max_pages, transport=t)
    else:
        reports = search_reports(query, order, transport=t)
    if limit:
        reports = reports[:limit]
    if verbose:
        print(f"search '{query}': {len(reports)} report(s) to dump")
    return dump_experiences(out_dir, [r.exp_id for r in reports],
                            transport=t, delay=delay, verbose=verbose)


def dump_substances(out_dir: str, listings: Iterable[SubstanceListing], *,
                    transport: Optional[Transport] = None,
                    delay: float = 1.0, verbose: bool = True) -> int:
    """Write one markdown file per substance summary page into ``{out_dir}/substances``."""
    t = transport or default_transport()
    folder = os.path.join(out_dir, "substances")
    os.makedirs(folder, exist_ok=True)
    written = 0
    for listing in listings:
        path = os.path.join(folder, f"{_slug(listing.name)}.md")
        if os.path.exists(path):
            if verbose:
                print(f"  skip substance {listing.name} (exists)")
            continue
        try:
            info = parse_substance_page(listing.url, transport=t)
        except Exception as e:  # noqa: BLE001 — one bad page must not kill a crawl
            if verbose:
                print(f"  err substance {listing.name}: {e}")
            continue
        time.sleep(delay)
        if _write_if_absent(path, lambda: substance_markdown(info)):
            written += 1
            if verbose:
                print(f"  wrote substance {info.name}")
    return written


def _category_listings(category: str, *, transport: Optional[Transport] = None
                       ) -> List[SubstanceListing]:
    from pyerowid.reports import _extract_list
    return _extract_list(category, transport=transport)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Dump an Erowid markdown corpus (one file per item).")
    parser.add_argument("--out", default="corpus", help="output folder (default: corpus)")
    parser.add_argument("--experiences", type=int, default=0,
                        help="dump experience ids 1..N (small sample for validation)")
    parser.add_argument("--ids", help="comma-separated explicit experience ids")
    parser.add_argument("--search", help="dump reports matching this query")
    parser.add_argument("--limit", type=int, default=10,
                        help="cap on --search reports (default: 10)")
    parser.add_argument("--all-pages", action="store_true",
                        help="paginate through all search result pages (use with --max-pages)")
    parser.add_argument("--max-pages", type=int, default=None,
                        help="cap pagination at this many pages (implies --all-pages)")
    parser.add_argument("--substances", choices=sorted(_CATEGORY_BASES),
                        help="dump a substance vault category index")
    parser.add_argument("--max-substances", type=int, default=5,
                        help="cap on --substances pages (default: 5)")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="seconds between live fetches (default: 1.0)")
    parser.add_argument("--transport", choices=["requests", "curl_cffi", "wayback", "flaresolverr"],
                        help="override the HTTP transport mode")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    transport = Transport(mode=args.transport) if args.transport else default_transport()
    verbose = not args.quiet
    total = 0

    if args.ids:
        ids = [int(x) for x in args.ids.split(",") if x.strip()]
        total += dump_experiences(args.out, ids, transport=transport,
                                  delay=args.delay, verbose=verbose)
    if args.experiences:
        total += dump_experiences(args.out, range(1, args.experiences + 1),
                                  transport=transport, delay=args.delay, verbose=verbose)
    if args.search:
        total += dump_search(args.out, args.search, limit=args.limit,
                             all_pages=args.all_pages, max_pages=args.max_pages,
                             transport=transport, delay=args.delay, verbose=verbose)
    if args.substances:
        listings = _category_listings(args.substances, transport=transport)[:args.max_substances]
        total += dump_substances(args.out, listings, transport=transport,
                                 delay=args.delay, verbose=verbose)

    if not any([args.ids, args.experiences, args.search, args.substances]):
        parser.error("nothing to do — pass --experiences, --ids, --search, or --substances")
    if verbose:
        print(f"\ndone — wrote {total} new markdown file(s) under {args.out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
