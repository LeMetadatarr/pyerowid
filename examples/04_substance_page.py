"""Example 04 — parse a substance vault summary page.

Run::

    python examples/04_substance_page.py
"""
import pyerowid


def main() -> None:
    info = pyerowid.parse_substance_page(
        "https://erowid.org/pharms/acetaminophen/acetaminophen.shtml")
    print(info.name)
    print("other names:", info.other_names)
    print("chem name:", info.chem_name)
    print("effects:", info.effects)
    print(info.description[:300])


if __name__ == "__main__":
    main()
