"""Script 5: send SPARQL queries from Python to a local endpoint (Oxigraph) and print the results.

Usage:  python scripts/run_queries.py     (start the endpoint first with: oxigraph serve --location store)
Input:  .rq files in the queries folder and the endpoint, both set in config.json
Output: one result table per query, printed to the terminal; an unreachable endpoint is logged as an error
Steps:  1 read the .rq file  2 send it and get JSON back  3 turn the JSON into rows  4 print a table
"""

import sys
from pathlib import Path
from urllib.error import URLError
from SPARQLWrapper import SPARQLWrapper, JSON
from common import get_logger, load_config

# Queries to run: (title, file name)
QUERIES = [
    ("CQ 3   Events per decision status", "cq3.rq"),
    ("CQ 10  Full supersession chain of decision D2a", "cq10.rq"),
    ("CQ 16  Decisions in force based on GDPR Art. 33", "cq16.rq"),
    ("Segments  Decision-bearing segments per status", "segments_by_status.rq"),
]


def run_query(endpoint, rq_path):
    """Run the query in one .rq file; return (column names, rows)."""
    sparql = SPARQLWrapper(endpoint)
    sparql.setQuery(Path(rq_path).read_text(encoding="utf-8"))
    sparql.setReturnFormat(JSON)
    data = sparql.queryAndConvert()
    columns = data["head"]["vars"]
    rows = []
    for binding in data["results"]["bindings"]:
        rows.append([shorten(binding[c]["value"]) if c in binding else "" for c in columns])
    return columns, rows


def shorten(value):
    """Keep only the last part of an IRI (after # or /) so tables stay readable; other values are unchanged."""
    if value.startswith("http"):
        return value.replace("#", "/").rsplit("/", 1)[-1]
    return value


def print_table(title, columns, rows):
    """Print the results as an aligned table."""
    print("\n" + title)
    widths = [max(len(c), *(len(r[i]) for r in rows)) if rows else len(c) for i, c in enumerate(columns)]
    print("  " + "  ".join(c.ljust(w) for c, w in zip(columns, widths)))
    for r in rows:
        print("  " + "  ".join(v.ljust(w) for v, w in zip(r, widths)))
    print(f"  ({len(rows)} rows)")


def main():
    config = load_config()
    log = get_logger("queries")
    for title, rq_file in QUERIES:
        try:
            columns, rows = run_query(config["endpoint"], Path(config["paths"]["queries"], rq_file))
        except URLError:
            log.error("Cannot reach %s. Is the endpoint running (oxigraph serve --location store)?", config["endpoint"])
            sys.exit(1)
        print_table(title, columns, rows)


if __name__ == "__main__":
    main()
