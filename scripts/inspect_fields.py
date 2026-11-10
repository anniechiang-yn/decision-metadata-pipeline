"""Report which fields an input JSON file has (structure only; never prints text, title or notes).

Usage:  python scripts/inspect_fields.py INPUT.json
Input:  a JSON array of segment records
Output: for each field, how many records have it, how many are filled, and the value types;
        then the counts of each decision_status value
"""

import json
import sys
from collections import Counter


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python scripts/inspect_fields.py INPUT.json")
    with open(sys.argv[1], encoding="utf-8") as f:
        records = json.load(f)

    print("Records:", len(records))
    keys = Counter(k for r in records for k in r)
    for k, n in sorted(keys.items()):
        types = Counter(type(r[k]).__name__ for r in records if k in r)
        filled = sum(1 for r in records if r.get(k) not in (None, "", []))
        print(f"{k:<20} present {n:>4}  filled {filled:>4}  types {dict(types)}")
    print("decision_status values:", Counter(r.get("decision_status") for r in records))


if __name__ == "__main__":
    main()
