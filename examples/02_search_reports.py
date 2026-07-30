"""Example 02 — search experience reports.

Run::

    python examples/02_search_reports.py
"""
import pyerowid


def main() -> None:
    for r in pyerowid.search_reports("LSD", order="recent")[:10]:
        print(r.exp_id, "|", r.substance, "|", r.name, "—", r.author)


if __name__ == "__main__":
    main()
