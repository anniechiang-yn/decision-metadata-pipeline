# Report which fields an input JSON file has (structure only; never prints text, title or notes)
# Usage: python scripts/inspect_fields.py INPUT.json
import json, sys
from collections import Counter

records = json.load(open(sys.argv[1], encoding="utf-8"))
print("Records:", len(records))
keys = Counter(k for r in records for k in r)
for k, n in sorted(keys.items()):
    types = Counter(type(r[k]).__name__ for r in records if k in r)
    filled = sum(1 for r in records if r.get(k) not in (None, "", []))
    print(f"{k:<20} present {n:>4}  filled {filled:>4}  types {dict(types)}")
print("decision_status values:", Counter(r.get("decision_status") for r in records))
