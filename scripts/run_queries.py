# Script 5: send SPARQL queries from Python to a local endpoint (Oxigraph) and print the results
# Input:  .rq files in queries/; endpoint http://localhost:7878/query (start it with oxigraph serve)
# Output: one result table per query, printed to the terminal
# Steps:  1 read the .rq file  2 send it and get JSON back  3 turn the JSON into rows  4 print a table

from pathlib import Path
from SPARQLWrapper import SPARQLWrapper, JSON

ENDPOINT = "http://localhost:7878/query"

# Queries to run: (title, file name)
QUERIES = [
    ("CQ 3   Events per decision status", "cq3.rq"),
    ("CQ 10  Full supersession chain of decision D2a", "cq10.rq"),
    ("CQ 16  Decisions in force based on GDPR Art. 33", "cq16.rq"),
    ("Segments  Decision-bearing segments per status", "segments_by_status.rq"),
]


def run_query(rq_file):
    """Run the query in one .rq file; return (column names, rows)."""
    sparql = SPARQLWrapper(ENDPOINT)
    sparql.setQuery(Path("queries", rq_file).read_text(encoding="utf-8"))
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


if __name__ == "__main__":
    for title, rq_file in QUERIES:
        columns, rows = run_query(rq_file)
        print_table(title, columns, rows)
