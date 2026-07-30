"""Example 05 — a random experience report.

Run::

    python examples/05_random_experience.py
"""
import pyerowid


def main() -> None:
    exp = pyerowid.random_experience()
    if exp:
        print(exp.exp_id, exp.name, "—", exp.substance, "—", exp.year)


if __name__ == "__main__":
    main()
