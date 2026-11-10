"""Script 6: validate converted segment data against the SHACL shapes.

Usage:  python scripts/validate.py DATA.ttl
Input:  a Turtle file written by scripts/convert_batch.py; the shapes and vocabulary set in config.json
Output: a summary (one line per violation) in the terminal and in DATA.ttl.shacl.log, and two reports:
        DATA.ttl.shacl.txt (full report for people) and DATA.ttl.shacl.ttl (report as RDF)
        Exit code 0 if the data conforms, 1 if it does not (so it can be chained after the conversion)
Steps:  1 load the data together with the vocabulary  2 validate against the shapes
        3 log each violation  4 write the reports
"""

import sys
from rdflib import Graph, Namespace
from pyshacl import validate
from common import get_logger, load_config

SH = Namespace("http://www.w3.org/ns/shacl#")


def load_data(data_path, vocabulary_path):
    """Merge the data with the vocabulary: the status rule reads skos:inScheme and skos:broader from it.
    (pyshacl's ont_graph option does not work here: it only takes RDFS and OWL definitions.)"""
    g = Graph()
    g.parse(data_path)
    g.parse(vocabulary_path)
    return g


def summarise(results_graph):
    """One line per top-level violation: segment, property, rule that failed."""
    lines = []
    # sh:result links the report to its top-level results; nested details use sh:detail and are skipped
    for result in results_graph.objects(predicate=SH.result):
        focus = results_graph.value(result, SH.focusNode)
        path = results_graph.value(result, SH.resultPath)
        rule = results_graph.value(result, SH.sourceConstraintComponent)
        lines.append("%s  %s  %s" % (
            str(focus).split("/")[-1],
            str(path).split("#")[-1],
            str(rule).split("#")[-1].replace("ConstraintComponent", ""),
        ))
    return sorted(lines)


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python scripts/validate.py DATA.ttl")
    data_path = sys.argv[1]
    config = load_config()
    log = get_logger("validate", data_path + ".shacl.log")

    # Step 1: load the data together with the vocabulary
    g = load_data(data_path, config["paths"]["vocabulary"])

    # Step 2: validate against the shapes
    conforms, results_graph, results_text = validate(g, shacl_graph=config["paths"]["shapes"])

    # Step 3: log each violation
    lines = summarise(results_graph)
    log.info("Conforms: %s (%d violation(s))", conforms, len(lines))
    for line in lines:
        log.warning("  %s", line)

    # Step 4: write the reports
    with open(data_path + ".shacl.txt", "w", encoding="utf-8") as f:
        f.write(results_text)
    results_graph.serialize(data_path + ".shacl.ttl", format="turtle")
    log.info("Reports written to %s.shacl.txt and %s.shacl.ttl", data_path, data_path)

    sys.exit(0 if conforms else 1)


if __name__ == "__main__":
    main()
