"""Script 2: print the broader/narrower hierarchy of the vocabulary as an indented tree.

Usage:  python scripts/concept_tree.py
Input:  the vocabulary file set in config.json (paths.vocabulary)
Output: prints the tree; each narrower concept is indented one level below its broader concept
Steps:  1 parse  2 find the top concepts  3 print each top concept and, recursively, its narrower concepts
"""

from rdflib import Graph, RDF
from rdflib.namespace import SKOS
from common import load_config


def label_en(g, concept):
    """Return the English prefLabel of a concept."""
    for value in g.objects(concept, SKOS.prefLabel):
        if value.language == "en":
            return str(value)
    return str(concept)


def children(g, concept):
    """Narrower concepts. The file only states skos:broader (narrower -> broader),
    so look for the concepts whose broader is this one."""
    return sorted(g.subjects(SKOS.broader, concept), key=lambda c: label_en(g, c))


def print_tree(g, concept, depth):
    """Print this concept, then each narrower concept one level deeper (recursive)."""
    print("    " * depth + "- " + label_en(g, concept))
    for child in children(g, concept):
        print_tree(g, child, depth + 1)


def main():
    config = load_config()

    # Step 1: parse
    g = Graph()
    g.parse(config["paths"]["vocabulary"])

    # Step 2: top concepts are the ones the concept scheme points to with skos:hasTopConcept
    scheme = next(g.subjects(RDF.type, SKOS.ConceptScheme))
    tops = sorted(g.objects(scheme, SKOS.hasTopConcept), key=lambda c: label_en(g, c))

    # Step 3: print from each top concept down
    for top in tops:
        print_tree(g, top, 0)


if __name__ == "__main__":
    main()
