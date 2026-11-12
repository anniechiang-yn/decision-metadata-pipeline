"""Script 10: run each demo query with and without the status filter and write the results side by side.

Usage:  python scripts/compare.py     (endpoint running on the demo store; Ollama running, or MOCK=1)
Input:  the corpus and the queries set in config.json (demo/corpus.json, demo/queries.json)
Output: a Markdown file (output/comparison.md) with, per query:
          A  no filter: the top-k segments by similarity over the whole corpus
          B  filter first: the top-k segments among those whose status matches the condition
          C  B plus the segments that the B results link to (only for queries with "expand": true)
        Every result shows its decision status; results in the expected answer are marked.
Steps:  1 read corpus and queries  2 embed segment texts and query texts  3 for each query,
        rank, filter, expand  4 write the comparison
Note:   a small demonstration of the mechanism. It makes no claim about retrieval performance.
"""

import json
import sys
from pathlib import Path
from urllib.error import URLError
from common import get_logger, load_config
from embed import MOCK, cosine, embed_texts
from filter_segments import expand_related, segments_by_status


def rank(query_vector, vectors, candidates, top_k):
    """Return the top_k candidate IDs, most similar to the query first."""
    scored = sorted(candidates, key=lambda segment_id: cosine(query_vector, vectors[segment_id]), reverse=True)
    return scored[:top_k]


def result_lines(segment_ids, records, expected, note=""):
    """One Markdown line per result: ID, status, title, and a mark if it is in the expected answer."""
    lines = []
    for segment_id in segment_ids:
        record = records[segment_id]
        mark = " ✔" if segment_id in expected else ""
        lines.append(f"- {segment_id} [{record['decision_status']}] {record['title']}{note}{mark}")
    return lines or ["- (none)"]


def found_line(segment_ids, expected):
    """Say how many of the segments shown are in the expected answer, and how large that answer is.

    The size is stated because top_k can be smaller than the expected answer: 3 shown out of an
    expected 6 cannot find more than 3.
    """
    found = len(set(segment_ids) & set(expected))
    return f"In the expected answer: {found} of the {len(segment_ids)} shown (expected answer has {len(expected)})"


def main():
    config = load_config()
    log = get_logger("compare")
    demo = config["demo"]
    corpus = json.loads(Path(demo["corpus"]).read_text(encoding="utf-8"))
    queries = json.loads(Path(demo["queries"]).read_text(encoding="utf-8"))
    records = {record["segment_id"]: record for record in corpus}
    ids = list(records)

    try:
        segment_vectors = embed_texts(config, [records[i]["text"] for i in ids])
        query_vectors = embed_texts(config, [q["query"] for q in queries])
    except URLError:
        log.error("Cannot reach %s. Is Ollama running?", config["embedding"]["url"])
        sys.exit(1)
    vectors = dict(zip(ids, segment_vectors))

    out = ["# Retrieval with and without the status filter", ""]
    if MOCK:
        out += ["MOCK run: the vectors are made up, so the rankings below mean nothing.", ""]
    for q, query_vector in zip(queries, query_vectors):
        expected = q["expected"]
        try:
            allowed = segments_by_status(config, q["concepts"])
            top_all = rank(query_vector, vectors, ids, demo["top_k"])
            top_filtered = rank(query_vector, vectors, [i for i in ids if i in allowed], demo["top_k"])
            linked = sorted(expand_related(config, top_filtered, q["keep_history"])) if q["expand"] else []
        except URLError:
            log.error("Cannot reach %s. Is the endpoint running?", config["endpoint"])
            sys.exit(1)
        out += [f"## {q['id']}  {q['query']}", "",
                f"Filter: {' or '.join(q['concepts'])} ({len(allowed)} of {len(ids)} segments). "
                f"Expected answer (standard {q['standard']}): {', '.join(expected)}", "",
                "A. No filter", *result_lines(top_all, records, expected), found_line(top_all, expected), "",
                "B. Filter first", *result_lines(top_filtered, records, expected), found_line(top_filtered, expected), ""]
        if q["expand"]:
            history = "kept" if q["keep_history"] else "left out"
            out += [f"C. Filter first, then linked segments (superseded, abandoned and rejected ones {history})",
                    *result_lines(top_filtered, records, expected),
                    *(result_lines(linked, records, expected, " (linked)") if linked else []),
                    found_line(top_filtered + linked, expected), ""]
        log.info("%s done", q["id"])

    Path(demo["result"]).parent.mkdir(parents=True, exist_ok=True)
    Path(demo["result"]).write_text("\n".join(out) + "\n", encoding="utf-8")
    log.info("Written to %s", demo["result"])


if __name__ == "__main__":
    main()
