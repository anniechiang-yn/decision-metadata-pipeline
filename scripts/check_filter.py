"""Script 8: check the filter against answers worked out by hand from demo/corpus.json.

Usage:  python scripts/check_filter.py     (endpoint running on the demo store)
Input:  the three filter cases and three expansion cases below; the endpoint in config.json
Output: PASS or FAIL per case, with the missing and unexpected IDs; exit code 0 if all pass, 1 otherwise
"""

import sys
from urllib.error import URLError
from common import get_logger, load_config
from filter_segments import expand_related, segments_by_status

INFORMATIONAL = {"101_000", "102_000", "103_000", "104_000"}
ALL_SEGMENTS = {f"{conv}_{n:03d}" for conv in (101, 102, 103, 104) for n in range(6)}

# (description, concepts, expected segment IDs)
CASES = [
    ("one status", ["Exploring"], {"101_004", "102_004", "103_004", "104_004"}),
    ("two statuses", ["Decided", "Implemented"],
     {"101_003", "101_005", "102_001", "102_005", "103_001", "103_005", "104_001", "104_005"}),
    ("broader concept", ["DecisionBearing"], ALL_SEGMENTS - INFORMATIONAL),
]

# (description, segment IDs to expand, keep_history, expected linked segment IDs)
EXPANSION_CASES = [
    ("linked informational segment", ["102_001"], False, {"102_000"}),
    ("linked superseded segment, current state", ["103_001"], False, set()),
    ("linked superseded segment, history kept", ["103_001"], True, {"103_003"}),
]


def main():
    config = load_config()
    log = get_logger("check_filter")
    failed = 0
    for description, concepts, expected in CASES:
        try:
            found = segments_by_status(config, concepts)
        except URLError:
            log.error("Cannot reach %s. Is the endpoint running?", config["endpoint"])
            sys.exit(1)
        if found == expected:
            log.info("PASS %s: %s -> %d segment(s)", description, " or ".join(concepts), len(found))
        else:
            failed += 1
            log.error("FAIL %s: missing %s, unexpected %s", description,
                      sorted(expected - found), sorted(found - expected))
    for description, segment_ids, keep_history, expected in EXPANSION_CASES:
        found = expand_related(config, segment_ids, keep_history)
        if found == expected:
            log.info("PASS %s: %s -> %s", description, ", ".join(segment_ids), sorted(found) or "nothing")
        else:
            failed += 1
            log.error("FAIL %s: missing %s, unexpected %s", description,
                      sorted(expected - found), sorted(found - expected))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
