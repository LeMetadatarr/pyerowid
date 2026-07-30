"""Example 01 — fetch a single experience report.

Run::

    python examples/01_get_experience.py
"""
import pyerowid


def main() -> None:
    exp = pyerowid.get_experience(1)
    if exp is None:
        print("no report")
        return
    print(exp.name, "—", exp.substance, "—", exp.year)
    print("author:", exp.author, "| age:", exp.age, "| gender:", exp.gender)
    for d in exp.dosage:
        print(f"  {d.time}  {d.amount}  {d.method}  {d.substance}")
    print("\n", exp.text[:300])


if __name__ == "__main__":
    main()
