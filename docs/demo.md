# Demo: filtering by decision status before vector retrieval

A small, runnable demonstration of one mechanism: use the graph to decide which segments may be ranked, then rank only those by text similarity. Everything here is fictional.

## Why

Text similarity cannot tell a current decision from a dropped one. "We decided to keep CVs for 6 months" and "We decided to keep CVs for 12 months" are nearly the same sentence; only the metadata says the second was replaced. In an earlier ablation study ([doi:10.5281/zenodo.21915438](https://doi.org/10.5281/zenodo.21915438)), constraining the candidate set by decision status at query time accounted for about 60% of the recall gain on a 47-segment corpus. That study hard-coded the filter in Python. Here the same filter is a SPARQL query over the converted metadata and the Decision Status Vocabulary.

## Limitations

Read these before the results.

- **This shows a mechanism, not performance.** 24 fictional segments and 6 queries, written by the same person who built the filter. No statistics are computed and none should be inferred.
- **The filter condition is given, not detected.** Each query in `demo/queries.json` states which statuses it wants. Working out the condition from the question is a separate problem and is not attempted.
- **Three results are shown per query**, while some expected answers have four to six segments. Each result block therefore states both numbers.
- **The corpus was written to contain the hard cases**: near-identical wording with opposite statuses. Real corpora will contain fewer clean pairs.
- **Expected answers** were labelled by hand by a single annotator, before the comparison was run. Each query states the labelling standard: A, segments that are in force and answer the question directly; B, any segment that is part of the answer, including background and history.
- **Expansion follows links one step, outwards, from the three ranked results.** It can only bring back what an annotator linked.

## What it does

```
demo/corpus.json (text + metadata)
   │ text ───────────────────────────────►  scripts/embed.py      bge-m3 vectors (local, via Ollama)
   │ metadata                                        │
   ▼                                                 │
convert_batch.py → validate.py → Oxigraph            │
   ▼                                                 ▼
scripts/filter_segments.py                  scripts/compare.py
   segments_by_status()  ── allowed IDs ──►   A  no filter:     top 3 of all segments
   expand_related()      ── linked IDs  ──►   B  filter first:  top 3 of the allowed segments
                                              C  B plus the segments that B's results link to
                                                     ▼
                                              output/comparison.md
```

The segment text never enters the graph (see `docs/mapping.md`); the graph holds the metadata and decides eligibility, the vectors decide order.

Two things the graph does that a status column in a table would not:

- **A broader concept matches everything below it.** The filter uses `skos:broader*`, so `DecisionBearing` selects all six narrower statuses without listing them. A status added to the vocabulary later is picked up without changing the code.
- **Links bring back what the filter removed.** A hard filter on decision statuses drops informational segments, including the ones a decision rests on. `expand_related()` follows `dcterms:relation` from the ranked results and returns the linked segments. A switch controls history: for a question about the current state, linked segments that are Superseded, Abandoned or Rejected are left out; for a question about how a decision came about, they are kept. Every result is printed with its status either way, so an outdated segment is never shown as if it were in force.

## How this differs from GraphRAG

GraphRAG usually refers to the approach published by Microsoft Research ([arXiv:2404.16130](https://arxiv.org/abs/2404.16130)): a language model extracts entities and relations from the text to build a graph, groups them into communities, and writes a summary of each community in advance; questions are then answered from those summaries. This demo is not that, in three respects.

| | GraphRAG | This demo |
|---|---|---|
| Question it addresses | Questions about a whole corpus, such as its main themes, that no single passage answers | Which of several similar passages states the decision currently in force |
| Where the graph comes from | Extracted from the text by a language model | Converted from human-annotated metadata, with status values from a controlled vocabulary, validated with SHACL |
| What the graph does at query time | Supplies pre-written community summaries | Decides which segments may be ranked, and follows links from the results; ranking is still done by vectors |

The two are complementary: decision-status metadata could be attached to an extracted graph. The cost of the approach here is the annotation it depends on, as D6 shows.

## Corpus and queries

`demo/corpus.json`: 24 segments from four fictional compliance discussions at a recruitment software company (CV retention, AI screening, data location, interview recording). Each discussion has one informational segment, a decision, its implementation, an option still being explored, and dropped or refused options; two discussions contain a superseded decision. The corpus converts 24 of 24 and conforms to the shapes.

| Query | Condition | Expansion | Standard |
|---|---|---|---|
| D1 How long do we keep the CVs of rejected candidates? | Decided or Implemented | no | A |
| D2 Can the AI tool reject candidates automatically? | Decided or Implemented | no | A |
| D3 Which proposals were dropped or refused? | Abandoned or Rejected | no | A |
| D4 What are we still evaluating? | Exploring | no | A |
| D5 What does the law require when we use AI to screen applications? | Decided or Implemented | yes, history left out | A |
| D6 What have we considered or decided before about letting the AI tool reject candidates automatically? | DecisionBearing | yes, history kept | B |

## Results

One run, bge-m3 through Ollama, top 3. Each cell: segments shown that are in the expected answer / size of the expected answer. Full output: `demo/comparison.md`.

| Query | A no filter | B filter first | C with links | What happened |
|---|---|---|---|---|
| D1 | 1 / 2 | 2 / 2 | | Without the filter, the superseded 12-month rule ranks second. |
| D2 | 1 / 2 | 2 / 2 | | Without the filter, the abandoned plan for automatic rejections ranks first. |
| D3 | 3 / 6 | 3 / 6 | | Identical. The top three were already dropped or refused proposals. |
| D4 | 2 / 4 | 3 / 4 | | The filter removes one decided segment from the top three. |
| D5 | 1 / 1 | 0 / 1 | 1 / 1 | The filter removes the informational segment that answers the question; the link from the decision brings it back. |
| D6 | 1 / 4 | 1 / 4 | 1 / 4 | Nothing helps. See below. |

**Where it did not help.**

- D3: the wording of the question ("dropped or refused") already matches the wording of the segments, so similarity alone finds the right statuses.
- D5, column B: a hard filter can remove the answer. This is the cost of filtering, and the reason for the expansion step.
- D6 fails for three reasons. The abandoned segment that ranks first has no links, so expansion has nowhere to go: the annotation is inconsistent, since a comparable segment in another discussion is linked. Expansion starts from three results, two of which are from the wrong topic, and one of them pulls in an unrelated decision. And the condition `DecisionBearing` removes only the four informational segments: the question is about a topic, and decision status does not separate topics. The corpus was left as it was after this run. Expansion is only as good as the links.

## Run it

After the environment set-up at the top of "Run it" in the README, with Ollama running and the model pulled (`ollama pull bge-m3`):

```
# convert and validate the demo corpus
python scripts/convert_batch.py demo/corpus.json output/corpus.ttl \
  && python scripts/validate.py output/corpus.ttl

# a separate store, so the sample data does not mix into the filter results
rm -rf store-demo
oxigraph load --location store-demo --file data/decision-status.ttl
oxigraph load --location store-demo --file output/corpus.ttl

# start the endpoint (keep this terminal open; stop any other oxigraph serve first)
oxigraph serve --location store-demo

# in a second terminal
python scripts/check_filter.py     # expect six PASS lines
python scripts/compare.py          # writes output/comparison.md
```

`MOCK=1 python scripts/compare.py` runs without Ollama using made-up vectors. It tests the program flow only; the rankings mean nothing.
