"""Script 1: list every concept in the Decision Status Vocabulary with its labels and definition.

Usage:  python scripts/list_concepts.py
Input:  the vocabulary file set in config.json (paths.vocabulary)
Output: prints each concept's English label, Chinese label and definition
Steps:  1 parse the file into a Graph  2 find every skos:Concept  3 print labels and definition
"""

from rdflib import Graph, RDF
from rdflib.namespace import SKOS
from common import load_config


def pick_lang(g, subject, predicate, lang):
    """Return the value of `predicate` on `subject` in language `lang`, or None."""
    for value in g.objects(subject, predicate):
        if value.language == lang:
            return value
    return None


def main():
    config = load_config()

    # Step 1: parse
    g = Graph()
    g.parse(config["paths"]["vocabulary"])
    print("Triples:", len(g))

    # Step 2: find all concepts, sorted by notation so the output order is stable
    concepts = sorted(g.subjects(RDF.type, SKOS.Concept),
                      key=lambda c: str(g.value(c, SKOS.notation)))
    print("Concepts:", len(concepts))

    # Step 3: print
    for c in concepts:
        print()
        print(pick_lang(g, c, SKOS.prefLabel, "en"), "/", pick_lang(g, c, SKOS.prefLabel, "zh-hant"))
        print("  Definition:", g.value(c, SKOS.definition))


if __name__ == "__main__":
    main()
