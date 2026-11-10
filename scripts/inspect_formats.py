"""Report value formats of an input JSON file (never prints text, title or notes).

Usage:  python scripts/inspect_formats.py INPUT.json
Input:  a JSON array of segment records
Output: ID format problems, date formats (digits masked), L1 codes, link fields and the maturity range
"""

import json
import re
import sys
from collections import Counter
from common import ID_PATTERN


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python scripts/inspect_formats.py INPUT.json")
    with open(sys.argv[1], encoding="utf-8") as f:
        records = json.load(f)
    seg_ids = {r.get("segment_id") for r in records if r.get("segment_id")}

    print("Records without segment_id:", sum(1 for r in records if not r.get("segment_id")))
    print("segment_id values with an unexpected format:", [s for s in seg_ids if not ID_PATTERN.match(s)])
    # digits are replaced with 9 so only the format is shown, not the dates
    print("valid_from formats:", Counter(re.sub(r"\d", "9", r.get("valid_from") or "(empty)") for r in records))
    print("L1_codes values:", Counter(c for r in records for c in r.get("L1_codes") or []))
    for field in ["related_segments", "prerequisites"]:
        items = [x for r in records for x in r.get(field) or []]
        looks_like_id = sum(1 for x in items if isinstance(x, str) and ID_PATTERN.match(x))
        in_corpus = sum(1 for x in items if x in seg_ids)
        print(f"{field}: {len(items)} values, {looks_like_id} look like segment IDs, {in_corpus} found in this file")
    values = [r["maturity"] for r in records if isinstance(r.get("maturity"), (int, float))]
    print("maturity range:", (min(values), max(values)) if values else "(no values)")


if __name__ == "__main__":
    main()
