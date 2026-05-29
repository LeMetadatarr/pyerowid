"""Example 06 — serialise models to plain dicts / JSON.

Run::

    python examples/06_to_dict_json.py
"""
import json

import pyerowid


def main() -> None:
    exp = pyerowid.get_experience(1)
    if exp:
        print(json.dumps(exp.to_dict(), indent=2, ensure_ascii=False)[:500])


if __name__ == "__main__":
    main()
