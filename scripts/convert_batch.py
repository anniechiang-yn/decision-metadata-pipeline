# Script 4: batch-convert segment metadata (JSON) to RDF (Turtle)
# Usage:  python scripts/convert_batch.py INPUT.json OUTPUT.ttl
# Input:  a JSON array, one object per segment (fields in docs/mapping.md; missing fields are fine)
# Output: a Turtle file; problems are logged (terminal and OUTPUT.ttl.log) and skipped, never fatal
# Steps:  1 read the vocabulary and the JSON  2 convert each record, checking every value
#         3 check that no free text leaks into the output  4 write and summarise

import json
import logging
import re
import sys
from datetime import date
from rdflib import Graph, Literal, Namespace, RDF
from rdflib.namespace import DCTERMS, SKOS, XSD

SEG = Namespace("https://anniechiang-data.framer.website/ontology/segment#")
SEGD = Namespace("https://anniechiang-data.framer.website/data/segment/")
CONV = Namespace("https://anniechiang-data.framer.website/data/conversation/")
DS = Namespace("https://anniechiang-data.framer.website/vocab/decision-status#")

ID_PATTERN = re.compile(r"^\d{3}_\d{3}[a-z]?$")
NOT_CONVERTED = ["text", "title", "notes"]   # not converted (see docs/mapping.md)


def as_list(value):
    """Wrap a single value in a list; None or an empty string becomes an empty list."""
    if value in (None, ""):
        return []
    return value if isinstance(value, list) else [value]


def add_segment_refs(g, s, seg_id, record, field, prop, log):
    """Fields that link to other segments: valid IDs become IRIs, anything else is logged and skipped."""
    for v in as_list(record.get(field)):
        if isinstance(v, str) and ID_PATTERN.match(v):
            g.add((s, prop, SEGD[v]))
        else:
            log.warning("%s: %s value is not a segment ID, skipped", seg_id, field)


def add_decimal(g, s, seg_id, record, field, prop, log):
    """Numbers between 0 and 1 become xsd:decimal; anything else is logged and skipped."""
    v = record.get(field)
    if v is None:
        return
    if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 1:
        g.add((s, prop, Literal(str(v), datatype=XSD.decimal)))
    else:
        log.warning("%s: %s is not a number between 0 and 1, skipped", seg_id, field)


def add_date(g, s, seg_id, record, field, prop, log):
    """Dates must be valid YYYY-MM-DD dates to become xsd:date."""
    v = record.get(field)
    if v in (None, ""):
        return
    try:
        date.fromisoformat(v)
        g.add((s, prop, Literal(v, datatype=XSD.date)))
    except (TypeError, ValueError):
        log.warning("%s: %s is not a YYYY-MM-DD date, skipped", seg_id, field)


def convert_record(g, record, statuses, log):
    """Add one segment's triples to g. A record without a valid segment_id is skipped entirely."""
    seg_id = record.get("segment_id")
    if not (isinstance(seg_id, str) and ID_PATTERN.match(seg_id)):
        log.warning("A record has a missing or invalid segment_id, skipped")
        return False

    s = SEGD[seg_id]
    g.add((s, RDF.type, SEG.Segment))
    g.add((s, DCTERMS.identifier, Literal(seg_id)))
    g.add((s, DCTERMS.isPartOf, CONV[seg_id[:3]]))   # first three digits, copied as is

    status = record.get("decision_status")
    if status:
        if DS[status] in statuses:
            g.add((s, SEG.hasDecisionStatus, DS[status]))
        else:
            log.warning("%s: decision_status \"%s\" is not in the vocabulary, skipped", seg_id, status)

    add_decimal(g, s, seg_id, record, "maturity", SEG.maturity, log)
    add_decimal(g, s, seg_id, record, "importance", SEG.importance, log)
    add_date(g, s, seg_id, record, "valid_from", SEG.validFrom, log)
    add_date(g, s, seg_id, record, "valid_to", SEG.validTo, log)
    add_date(g, s, seg_id, record, "annotation_date", SEG.annotatedOn, log)
    add_segment_refs(g, s, seg_id, record, "superseded_by", DCTERMS.isReplacedBy, log)
    add_segment_refs(g, s, seg_id, record, "related_segments", DCTERMS.relation, log)
    add_segment_refs(g, s, seg_id, record, "conflict_with", SEG.conflictsWith, log)
    add_segment_refs(g, s, seg_id, record, "merge_target", SEG.mergedInto, log)

    for v in as_list(record.get("prerequisites")):
        g.add((s, SEG.prerequisiteNote, Literal(str(v))))
    for v in as_list(record.get("L1_codes")):
        g.add((s, DCTERMS.subject, Literal(str(v))))
    if record.get("annotator"):
        g.add((s, SEG.annotator, Literal(str(record["annotator"]))))
    return True


def leaked_values(g, records):
    """Leak check: do any values of the unconverted fields appear verbatim as literals in the output?"""
    blocked = {str(r[f]) for r in records for f in NOT_CONVERTED if r.get(f)}
    literals = {str(o) for o in g.objects() if isinstance(o, Literal)}
    return [v for v in literals if v in blocked]


def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: python scripts/convert_batch.py INPUT.json OUTPUT.ttl")
    in_path, out_path = sys.argv[1], sys.argv[2]

    # log to the terminal and to OUTPUT.ttl.log
    log = logging.getLogger("convert")
    log.setLevel(logging.INFO)
    for h in (logging.StreamHandler(), logging.FileHandler(out_path + ".log", mode="w", encoding="utf-8")):
        h.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        log.addHandler(h)

    # Step 1: read the vocabulary (to check status values) and the JSON
    vocab = Graph().parse("data/decision-status.ttl")
    statuses = set(vocab.subjects(RDF.type, SKOS.Concept))
    records = json.load(open(in_path, encoding="utf-8"))

    # Step 2: convert each record
    g = Graph()
    for prefix, ns in [("seg", SEG), ("segd", SEGD), ("conv", CONV), ("ds", DS), ("dcterms", DCTERMS)]:
        g.bind(prefix, ns)
    converted = sum(1 for r in records if convert_record(g, r, statuses, log))

    # Links to segments not in this file are reported but kept
    known = {SEGD[r["segment_id"]] for r in records if isinstance(r.get("segment_id"), str)}
    for p in (DCTERMS.isReplacedBy, DCTERMS.relation, SEG.conflictsWith, SEG.mergedInto):
        for s, o in g.subject_objects(p):
            if o not in known:
                log.info("%s links to %s, which is not in this file (link kept)", s.split("/")[-1], o.split("/")[-1])

    # Step 3: leak check; nothing is written if free text would leak
    leaks = leaked_values(g, records)
    if leaks:
        log.error("Output would contain %d value(s) from unconverted fields; nothing written", len(leaks))
        sys.exit(1)

    # Step 4: write and summarise
    g.serialize(out_path, format="turtle")
    log.info("Done: converted %d of %d records, %d triples, written to %s", converted, len(records), len(g), out_path)


if __name__ == "__main__":
    main()
