"""Script 7: return the IDs of the segments whose decision status matches a condition.

Usage:  python scripts/filter_segments.py Decided Implemented
        (start the endpoint first with: oxigraph serve --location store-demo)
Input:  one or more concept names from the decision-status vocabulary; the endpoint and namespaces in config.json
Output: the matching segment IDs, one per line, and a count
Steps:  1 check the concept names  2 build the SPARQL query  3 send it  4 collect the IDs
        expand_related() takes segment IDs and returns the segments they link to with dcterms:relation
Note:   a broader concept also matches every concept below it. DecisionBearing therefore returns
        segments with any of its six narrower statuses, without listing them here.
"""

import re
import sys
from urllib.error import URLError
from SPARQLWrapper import SPARQLWrapper, JSON
from common import ID_PATTERN, get_logger, load_config

NAME_PATTERN = re.compile(r"^[A-Za-z]+$")   # concept names are letters only; anything else is refused

QUERY = """
PREFIX seg:     <{seg}>
PREFIX ds:      <{ds}>
PREFIX skos:    <http://www.w3.org/2004/02/skos/core#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT DISTINCT ?id WHERE {{
  VALUES ?wanted {{ {wanted} }}
  ?status skos:broader* ?wanted .
  ?segment a seg:Segment ;
           seg:hasDecisionStatus ?status ;
           dcterms:identifier ?id .
}} ORDER BY ?id
"""

# Statuses that no longer state the current intent; left out of an expansion unless history is wanted
HISTORY = ["Superseded", "Abandoned", "Rejected"]

EXPAND_QUERY = """
PREFIX seg:     <{seg}>
PREFIX segd:    <{segd}>
PREFIX ds:      <{ds}>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT DISTINCT ?id WHERE {{
  VALUES ?hit {{ {hits} }}
  ?hit dcterms:relation ?related .
  ?related dcterms:identifier ?id .
  OPTIONAL {{ ?related seg:hasDecisionStatus ?status }}
  {history_filter}
}} ORDER BY ?id
"""


def run_select(config, query):
    """Send a SELECT query to the endpoint and return the set of ?id values."""
    sparql = SPARQLWrapper(config["endpoint"])
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    data = sparql.queryAndConvert()
    return {binding["id"]["value"] for binding in data["results"]["bindings"]}


def segments_by_status(config, concepts):
    """Return the set of segment IDs whose status is one of the concepts, or lies below one of them."""
    for name in concepts:
        if not NAME_PATTERN.match(name):
            raise ValueError(f"not a concept name: {name}")
    ns = config["namespaces"]
    wanted = " ".join("ds:" + name for name in concepts)
    return run_select(config, QUERY.format(seg=ns["seg"], ds=ns["ds"], wanted=wanted))


def expand_related(config, segment_ids, keep_history):
    """Return the IDs of the segments that the given segments link to with dcterms:relation.

    keep_history=False leaves out linked segments that are Superseded, Abandoned or Rejected,
    for questions about the current state. keep_history=True keeps them, for questions about
    how a decision came about. Segments already in segment_ids are not returned again.
    """
    for segment_id in segment_ids:
        if not ID_PATTERN.match(segment_id):
            raise ValueError(f"not a segment ID: {segment_id}")
    if not segment_ids:
        return set()
    ns = config["namespaces"]
    hits = " ".join("segd:" + segment_id for segment_id in segment_ids)
    if keep_history:
        history_filter = ""
    else:
        excluded = ", ".join("ds:" + name for name in HISTORY)
        history_filter = f"FILTER(!BOUND(?status) || ?status NOT IN ({excluded}))"
    query = EXPAND_QUERY.format(seg=ns["seg"], segd=ns["segd"], ds=ns["ds"], hits=hits, history_filter=history_filter)
    return run_select(config, query) - set(segment_ids)


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python scripts/filter_segments.py CONCEPT [CONCEPT ...]")
    config = load_config()
    log = get_logger("filter")
    try:
        ids = segments_by_status(config, sys.argv[1:])
    except URLError:
        log.error("Cannot reach %s. Is the endpoint running (oxigraph serve --location store-demo)?", config["endpoint"])
        sys.exit(1)
    for segment_id in sorted(ids):
        print(segment_id)
    log.info("%d segment(s) match %s", len(ids), " or ".join(sys.argv[1:]))


if __name__ == "__main__":
    main()
