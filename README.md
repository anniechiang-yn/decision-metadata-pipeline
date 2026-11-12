# Decision Metadata Pipeline

Converts segment-level decision metadata from AI conversation logs (JSON) into RDF, links each segment's decision status to a SKOS controlled vocabulary, validates the result with SHACL, and queries it over a SPARQL endpoint from Python. A small demo then uses the graph to filter candidates before vector retrieval.

Version 1.1. All data in this repository is fictional.

## Why

A retrieval system that only matches text cannot tell a current decision from one that was later dropped or replaced. In an earlier experiment ([rag-metadata-ablation](https://github.com/anniechiang-yn/rag-metadata-ablation)), filtering retrieval candidates by decision status accounted for about 60% of the recall gain. This pipeline puts that metadata into a graph, so the same filter can be written as a SPARQL query against a shared vocabulary instead of being hard-coded, and checks the graph before it is used.

## Pipeline

```
segment metadata (JSON)
   │  scripts/convert_batch.py   checks one value at a time; logs and skips invalid values; never writes free text
   ▼
RDF (Turtle)  ── status values point to the Decision Status Vocabulary (SKOS)
   │  scripts/validate.py         SHACL: rules across fields, across records, and on the vocabulary structure
   ▼                              exit code 1 stops the chain if the data does not conform
validated RDF
   │  oxigraph load
   ▼
SPARQL endpoint (Oxigraph, local)
   │  scripts/run_queries.py      SPARQLWrapper
   ▼
query results
```

## Demo: filtering before vector retrieval

Six queries over 24 fictional segments, each run with and without a decision-status filter and ranked with a local embedding model (bge-m3). It shows a mechanism and makes no claim about retrieval performance: the corpus is small, fictional and written to contain the hard cases.

| Query | No filter | Filter first | With linked segments |
|---|---|---|---|
| D1 current CV retention rule | 1 / 2 | 2 / 2 | |
| D2 can the AI reject automatically | 1 / 2 | 2 / 2 | |
| D3 dropped or refused proposals | 3 / 6 | 3 / 6 | |
| D4 options still being evaluated | 2 / 4 | 3 / 4 | |
| D5 what the law requires | 1 / 1 | 0 / 1 | 1 / 1 |
| D6 history of one decision | 1 / 4 | 1 / 4 | 1 / 4 |

Each cell: segments in the top three that are in the expected answer / size of the expected answer. The filter removes superseded and abandoned segments that plain similarity ranks first (D1, D2). It changes nothing where the question's wording already selects the right statuses (D3), removes the answer when the answer is informational (D5, restored by following links), and does not help a question about a topic's history (D6). Design, limitations, the reading of each result and how this differs from GraphRAG: [docs/demo.md](docs/demo.md).

## Known limitations

- SHACL checks structure, not meaning. A segment labelled Exploring that should have been Decided passes.
- Validation needs the vocabulary loaded together with the data: the status rule reads `skos:inScheme` and `skos:broader` from it. `scripts/validate.py` merges the two; pyshacl's `ont_graph` option does not work for this, because it only takes RDFS and OWL definitions.
- Links to other segments (`isReplacedBy`, `relation`, `conflictsWith`, `mergedInto`) are only checked to be IRIs. The target segment may sit outside the file, so its existence is reported by the converter but not enforced.
- The experiment's JSON has 11 of the 17 annotation fields. Missing fields are skipped and logged; the mapping and the shapes cover all 17, so rules on fields such as `valid_to` are only exercised by the sample and test data.
- Oxigraph does not run OWL reasoning, so questions that depend on inferred classes are not answered here.
- Load each file into the store once. Loading a file twice creates a second copy of its blank nodes (for example the ordered list in the vocabulary), and CQ 16 then returns every row twice. Step 4 below starts from an empty store for this reason.
- The demo filter takes the status condition as given; it does not work out the condition from the question. A concept name that is not in the vocabulary returns no segments rather than an error.
- The leak check only catches free text copied verbatim into the output.

## What has been checked

| Check | Data | Result |
|---|---|---|
| Conversion | `examples/sample_segments.json` (7 fictional records, some invalid on purpose) | 6 converted, 5 values logged and skipped, 1 record without an ID skipped |
| SHACL, clean data | Converted sample | Conforms (0 violations) |
| SHACL, dirty data | `tests/dirty_segments.json` (3 errors the converter cannot see) | 3 of 3 caught (4 violations, see below); the converter logged none of them |
| Queries | Sample data and the TalentFlow files | CQ 3, 10 and 16 return the same results as in GraphDB |
| Filter and expansion | `demo/corpus.json` (24 fictional segments), six cases worked out by hand | 6 of 6 pass (`scripts/check_filter.py`) |
| Comparison | Six demo queries, bge-m3 | One run, recorded in `demo/comparison.md` |
| Python | — | Pipeline scripts run on Python 3.13 and 3.9; demo scripts run on 3.13 |

The three test errors:

| Segment | Error | Why the converter lets it through | Rule that catches it |
|---|---|---|---|
| 990_000 | Status set to the structural concept Decision-bearing | It is a valid concept of the vocabulary | Status must have no narrower concept |
| 990_001 | `valid_to` earlier than `valid_from` | Each date is valid on its own | `validFrom` ≤ `validTo` |
| 990_002 | Same segment annotated twice with different statuses | Records are read one at a time | At most one status (and one annotation date) |

## Repository layout

| Path | Contents |
|---|---|
| `config.json` | Paths, endpoint and namespaces used by all scripts |
| `scripts/` | Python scripts (see below) |
| `shapes/segment-shapes.ttl` | SHACL shapes for converted segments |
| `data/decision-status.ttl` | Copy of the [Decision Status Vocabulary](https://github.com/anniechiang-yn/decision-status-skos) v1.1.0 |
| `examples/` | Fictional input (`sample_segments.json`) and the converter's output for it |
| `tests/dirty_segments.json` | Fictional input with three errors for the SHACL test |
| `demo/` | Fictional corpus with text (`corpus.json`), the six queries with expected answers (`queries.json`), and the recorded comparison |
| `queries/` | SPARQL queries |
| `docs/mapping.md` | Field-by-field mapping from JSON to RDF |
| `docs/demo.md` | Design, limitations and results of the demo |

Real annotation data is converted, validated and queried locally only; `.gitignore` excludes `output/` and the database folders.

## Scripts

| Script | What it does |
|---|---|
| `common.py` | Shared helpers: reads `config.json`, builds namespaces, sets up logging |
| `list_concepts.py` | Lists each vocabulary concept's labels and definition |
| `concept_tree.py` | Prints the vocabulary hierarchy as an indented tree |
| `inspect_fields.py`, `inspect_formats.py` | Report the fields and value formats of an input file without printing any free text |
| `convert_one.py` | Converts one hard-coded record, for checking the mapping by eye |
| `convert_batch.py` | Converts a JSON file to Turtle; invalid values are logged and skipped, and nothing is written if a free-text field would leak into the output |
| `validate.py` | Validates a Turtle file against the shapes; prints one line per violation, writes the full report (text and RDF), exits with 1 if the data does not conform |
| `run_queries.py` | Sends the queries in `queries/` to the local endpoint and prints the results |
| `filter_segments.py` | Demo. Returns the segments whose status matches a concept or lies below it; returns the segments that given segments link to, with or without superseded, abandoned and rejected ones |
| `check_filter.py` | Demo. Checks the filter and the expansion against six cases worked out by hand; exits with 1 if any fails |
| `embed.py` | Demo. Gets vectors from a local embedding model through Ollama, with a cache; computes cosine similarity |
| `compare.py` | Demo. Runs each query without the filter, with it, and with linked segments, and writes the results side by side |

Each script starts with a docstring giving its usage, input, output and steps. Run all scripts from the repository root.

## Run it

Requires Python 3.9 or later; 3.13 is recommended (3.9 no longer receives security updates).

```
python3 -m venv .venv            # use python3.13 if python3 points to an older version
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p output

# 1. convert and validate the sample data (validation runs only if the conversion succeeds)
python scripts/convert_batch.py examples/sample_segments.json output/sample_segments.ttl \
  && python scripts/validate.py output/sample_segments.ttl

# 2. the SHACL test: expect "Conforms: False (4 violation(s))" and exit code 1
python scripts/convert_batch.py tests/dirty_segments.json output/dirty.ttl \
  && python scripts/validate.py output/dirty.ttl

# 3. TalentFlow files used by three of the queries
curl -L -o data/talentflow.ttl https://raw.githubusercontent.com/anniechiang-yn/talentflow-ontology/main/talentflow.ttl
curl -L -o data/talentflow-sample-data.ttl https://raw.githubusercontent.com/anniechiang-yn/talentflow-ontology/main/examples/talentflow-sample-data.ttl

# 4. load everything into a new, empty Oxigraph store
rm -rf store
for f in data/decision-status.ttl data/talentflow.ttl data/talentflow-sample-data.ttl output/sample_segments.ttl; do
  oxigraph load --location store --file "$f"
done

# 5. start the endpoint (keep this terminal open), then run the queries in a second terminal
oxigraph serve --location store
python scripts/run_queries.py
```

To change a path, the endpoint or a namespace, edit `config.json`.

The demo uses its own store and needs Ollama; its steps are in [docs/demo.md](docs/demo.md#run-it).

## Design decisions

- **Two layers of checking.** The converter checks one value at a time (format, range, known concept) and skips what it cannot convert. SHACL checks what a single value cannot show: the order of two dates, duplicate records, and whether a status is a structural concept.
- **Status values are checked against the vocabulary, not a list.** The shape requires a concept of the Decision Status scheme with no narrower concept, instead of listing allowed values with `sh:in`. A new concept in the vocabulary needs no change to the shapes, and structural concepts such as Decision-bearing are excluded without being named.
- **At most one status, checked by SHACL rather than OWL.** Declaring the property functional in OWL would make a reasoner conclude that two different status values are the same concept (OWL has no unique name assumption), hiding the error. SHACL reports it.
- **Empty status is not converted.** An unassigned record is a data-quality state, not a decision state, so the status is optional in the shapes.
- **`seg:hasDecisionStatus`, not the TalentFlow property.** `tf:hasDecisionStatus` has the domain `tf:Decision`, so a reasoner would classify every segment as a TalentFlow decision.
- **The demo filters through the vocabulary hierarchy.** The query matches a concept and everything below it with `skos:broader*`, so a condition can name a broader concept and a new status needs no code change.
- **Linked segments are added after filtering, with a history switch.** A hard filter on decision statuses also drops the informational segments that decisions rest on; following `dcterms:relation` from the results brings them back. Whether superseded, abandoned and rejected segments come back too depends on the question: left out for the current state, kept for the history of a decision. Every result is shown with its status.
- **Settings in one file.** Paths, the endpoint, namespaces and the embedding model live in `config.json`. JSON rather than TOML, because Python reads JSON without extra packages on every supported version.

## Licence

Code: MIT. The Decision Status Vocabulary in `data/` is CC BY 4.0.
