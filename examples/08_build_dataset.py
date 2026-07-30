"""Example 08 — dump a small markdown corpus.

Writes one markdown file per item (YAML front-matter + body) into ``corpus/``.
The dump is resumable (re-running skips files already written) and polite (one
shared session, a delay between fetches). Validate on a tiny sample — Erowid has
100k+ experience ids, so a full crawl is a homelab job (see docs/dataset.md).

Run::

    python examples/08_build_dataset.py
    # equivalently, via the CLI:
    #   python -m pyerowid.dataset --out corpus --search LSD --limit 3
    #   python -m pyerowid.dataset --out corpus --substances pharms --max-substances 3
"""
import pyerowid
from pyerowid import dataset

OUT = "corpus"


def main() -> None:
    # A handful of experience reports, by explicit id.
    n = dataset.dump_experiences(OUT, [1, 2, 14], delay=1.0)
    print(f"experiences: wrote {n} new file(s)")

    # A few reports matching a search.
    n = dataset.dump_search(OUT, "LSD", limit=3, order="recent", delay=1.0)
    print(f"search: wrote {n} new file(s)")

    # A few substance summary pages from the pharms vault.
    listings = pyerowid.get_pharms()[:3]
    n = dataset.dump_substances(OUT, listings, delay=1.0)
    print(f"substances: wrote {n} new file(s)")

    print(f"\ncorpus at ./{OUT}/ — re-run to resume (existing files are skipped)")


if __name__ == "__main__":
    main()
