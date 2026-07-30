"""Example 03 — browse the substance vaults.

Run::

    python examples/03_browse_vaults.py
"""
import pyerowid


def main() -> None:
    print("categories:", pyerowid.get_categories()[:8])
    for s in pyerowid.get_pharms()[:8]:
        print(s.name, "—", s.other_names, "—", s.effects)


if __name__ == "__main__":
    main()
