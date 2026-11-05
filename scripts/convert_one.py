# Script 3: convert one hand-made (fictional) segment record to RDF following docs/mapping.md
# Input:  the `record` below (fictional values; all 17 fields plus L1_codes are filled)
# Output: prints Turtle and saves it to output/sample_one.ttl
# Steps:  1 define namespaces  2 create the subject (segment IRI)  3 add triples field by field  4 write

from pathlib import Path
from rdflib import Graph, Literal, Namespace, RDF
from rdflib.namespace import DCTERMS, XSD

# Step 1: namespaces (see the Namespaces table in docs/mapping.md)
SEG = Namespace("https://anniechiang-data.framer.website/ontology/segment#")
SEGD = Namespace("https://anniechiang-data.framer.website/data/segment/")
CONV = Namespace("https://anniechiang-data.framer.website/data/conversation/")
DS = Namespace("https://anniechiang-data.framer.website/vocab/decision-status#")

# Fictional record: none of these values come from real data
record = {
    "segment_id": "900_001",
    "title": "(fictional title, not converted)",
    "text": "(fictional text, not converted)",
    "notes": "(fictional notes, not converted)",
    "decision_status": "Decided",
    "maturity": 0.8,
    "importance": 0.6,
    "valid_from": "2026-03-02",
    "valid_to": "2026-04-15",
    "superseded_by": "900_004",
    "related_segments": ["900_002", "900_003"],
    "prerequisites": ["Finish the SPARQL course first"],
    "conflict_with": ["900_005"],
    "merge_target": "",
    "L1_codes": ["Technical"],
    "annotation_date": "2026-06-20",
    "annotator": "annotator-1",
}

g = Graph()
g.bind("seg", SEG)
g.bind("segd", SEGD)
g.bind("conv", CONV)
g.bind("ds", DS)
g.bind("dcterms", DCTERMS)

# Step 2: the subject is the segment's IRI
seg_id = record["segment_id"]
s = SEGD[seg_id]
g.add((s, RDF.type, SEG.Segment))
g.add((s, DCTERMS.identifier, Literal(seg_id)))

# Step 3: add triples field by field
# conversation: first three digits of segment_id, copied as is
g.add((s, DCTERMS.isPartOf, CONV[seg_id[:3]]))

# decision_status: an IRI pointing to a concept in the SKOS vocabulary; empty values are skipped
if record["decision_status"]:
    g.add((s, SEG.hasDecisionStatus, DS[record["decision_status"]]))

# numbers: xsd:decimal; None is skipped
for field, prop in [("maturity", SEG.maturity), ("importance", SEG.importance)]:
    if record[field] is not None:
        g.add((s, prop, Literal(str(record[field]), datatype=XSD.decimal)))

# dates: xsd:date; empty values are skipped
for field, prop in [("valid_from", SEG.validFrom), ("valid_to", SEG.validTo),
                    ("annotation_date", SEG.annotatedOn)]:
    if record[field]:
        g.add((s, prop, Literal(record[field], datatype=XSD.date)))

# links to other segments: IRIs. Single values are wrapped in a list so all four fields share one loop
for field, prop in [("superseded_by", DCTERMS.isReplacedBy),
                    ("related_segments", DCTERMS.relation),
                    ("conflict_with", SEG.conflictsWith),
                    ("merge_target", SEG.mergedInto)]:
    values = record[field] if isinstance(record[field], list) else [record[field]]
    for v in values:
        if v:
            g.add((s, prop, SEGD[v]))

# text values: literals
for v in record["prerequisites"]:
    g.add((s, SEG.prerequisiteNote, Literal(v)))
for v in record["L1_codes"]:
    g.add((s, DCTERMS.subject, Literal(v)))
if record["annotator"]:
    g.add((s, SEG.annotator, Literal(record["annotator"])))

# title, text and notes are not converted (see docs/mapping.md)

# Step 4: write
turtle = g.serialize(format="turtle")
print(turtle)
Path("output").mkdir(exist_ok=True)
Path("output/sample_one.ttl").write_text(turtle, encoding="utf-8")
print("Triples:", len(g), "- saved to output/sample_one.ttl")
