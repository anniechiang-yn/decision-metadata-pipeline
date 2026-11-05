# Decision Metadata Pipeline

Converts segment-level decision metadata from AI conversation logs (JSON) into RDF, links each segment's decision status to a SKOS controlled vocabulary, and queries the result over a SPARQL endpoint from Python.

Status: work in progress (version 0.1). SHACL validation and a v1.0 release are planned next.

## Why

A retrieval system that only matches text cannot tell a current decision from one that was later dropped or replaced. In an earlier experiment ([rag-metadata-ablation](https://github.com/anniechiang-yn/rag-metadata-ablation)), filtering retrieval candidates by decision status accounted for about 60% of the recall gain. This pipeline puts that metadata into a graph, so the same filter can be written as a SPARQL query against a shared vocabulary instead of being hard-coded.

## Pipeline

```
segment metadata (JSON)
   │  scripts/convert_batch.py   checks each value, logs problems, skips free text
   ▼
RDF (Turtle)  ── status values point to the Decision Status Vocabulary (SKOS)
   │  oxigraph load
   ▼
SPARQL endpoint (Oxigraph, local)
   │  scripts/run_queries.py      SPARQLWrapper
   ▼
query results
```

## Repository layout

| Path | Contents |
|---|---|
| `scripts/` | Python scripts (see below) |
| `data/decision-status.ttl` | Copy of the [Decision Status Vocabulary](https://github.com/anniechiang-yn/decision-status-skos) v1.1.0 |
| `examples/sample_segments.json` | Fictional input: seven segments, including one with invalid values, one without an ID and one with only the fields of the original experiment |
| `examples/sample_segments.ttl` | Output of the converter for the sample input |
| `queries/` | SPARQL queries |
| `docs/mapping.md` | Field-by-field mapping from JSON to RDF |

All data in this repository is fictional. Real annotation data is converted and queried locally only; `.gitignore` excludes `output/` and the database folder.

## Scripts

| Script | What it does |
|---|---|
| `list_concepts.py` | Reads the vocabulary and lists each concept's labels and definition |
| `concept_tree.py` | Prints the vocabulary hierarchy as an indented tree |
| `inspect_fields.py`, `inspect_formats.py` | Report the fields and value formats of an input file without printing any free text |
| `convert_one.py` | Converts one hard-coded record, for checking the mapping by eye |
| `convert_batch.py` | Converts a JSON file to Turtle; invalid values are logged and skipped, and the output is not written if any free-text field would leak into it |
| `run_queries.py` | Sends the queries in `queries/` to the local endpoint and prints the results |

## Run it

Requires Python 3.9 or later.

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# convert the sample data
mkdir -p output
python scripts/convert_batch.py examples/sample_segments.json output/sample_segments.ttl

# TalentFlow files used by three of the queries
curl -L -o data/talentflow.ttl https://raw.githubusercontent.com/anniechiang-yn/talentflow-ontology/main/talentflow.ttl
curl -L -o data/talentflow-sample-data.ttl https://raw.githubusercontent.com/anniechiang-yn/talentflow-ontology/main/examples/talentflow-sample-data.ttl

# load everything into a local Oxigraph store
for f in data/decision-status.ttl data/talentflow.ttl data/talentflow-sample-data.ttl output/sample_segments.ttl; do
  oxigraph load --location store --file "$f"
done

# start the endpoint (keep this terminal open), then run the queries in a second terminal
oxigraph serve --location store
python scripts/run_queries.py
```

## Queries

| File | Question | Technique |
|---|---|---|
| `segments_by_status.rq` | How many decision-bearing segments are there under each status? | `skos:broader*` over the vocabulary, aggregation |
| `cq3.rq` | How many TalentFlow events are there under each decision status? | Aggregation |
| `cq10.rq` | Which decisions replaced decision D2a, along the full chain? | Property path |
| `cq16.rq` | Which decisions still in force are based on GDPR Art. 33? | `FILTER NOT EXISTS`, SKOS ordered collection |

The three CQ queries come from [talentflow-ontology](https://github.com/anniechiang-yn/talentflow-ontology). They are included to show that the same queries return the same results from GraphDB and, through Python, from Oxigraph. Only the comment lines differ from the originals.

## Known limitations

- The experiment's JSON has 11 of the 17 annotation fields. Missing fields are skipped and logged; the mapping covers all 17.
- Oxigraph does not run OWL reasoning, so questions that depend on inferred classes are not answered here.
- The leak check only catches free text copied verbatim into the output.

## Licence

Code: MIT. The Decision Status Vocabulary in `data/` is CC BY 4.0.
