# Mapping: segment metadata (JSON) → RDF

Input: one JSON object per conversation segment (fields from the annotation schema of the RAG metadata experiment).
Output: Turtle, one resource per segment.

## Namespaces

| Prefix | IRI | Used for |
|---|---|---|
| `seg:` | `https://anniechiang-data.framer.website/ontology/segment#` | Custom properties and the `Segment` class |
| `segd:` | `https://anniechiang-data.framer.website/data/segment/` | Segment resources (one IRI per `segment_id`) |
| `conv:` | `https://anniechiang-data.framer.website/data/conversation/` | Conversation resources |
| `ds:` | `https://anniechiang-data.framer.website/vocab/decision-status#` | Decision Status Vocabulary (SKOS) |
| `dcterms:` | `http://purl.org/dc/terms/` | Standard metadata terms |

## Field mapping

| JSON field | RDF property | Object | Rule |
|---|---|---|---|
| `segment_id` | (subject) + `dcterms:identifier` | IRI `segd:{id}` + literal | Required. A record without it is skipped and logged. |
| — | `rdf:type` | `seg:Segment` | Added to every segment. |
| `conversation_id` | `dcterms:isPartOf` | IRI `conv:{id}` | Not present in the experiment JSON; derived from the first three digits of `segment_id`. The number is copied as is, never recalculated (see note 2). |
| `decision_status` | `seg:hasDecisionStatus` | IRI `ds:{value}` | Value must be a concept in the vocabulary. Empty value: not converted (unassigned is a data-quality state, not a decision state). Unknown value: skipped and logged. |
| `maturity` | `seg:maturity` | `xsd:decimal` | 0–1. `null`: not converted. |
| `importance` | `seg:importance` | `xsd:decimal` | 0–1. `null`: not converted. |
| `valid_from` | `seg:validFrom` | `xsd:date` | Format `YYYY-MM-DD`. |
| `valid_to` | `seg:validTo` | `xsd:date` | Empty means still valid: not converted. |
| `superseded_by` | `dcterms:isReplacedBy` | IRI `segd:{id}` | |
| `related_segments` | `dcterms:relation` | IRI `segd:{id}` | One triple per listed segment. |
| `conflict_with` | `seg:conflictsWith` | IRI `segd:{id}` | |
| `merge_target` | `seg:mergedInto` | IRI `segd:{id}` | Records a manual merge of an over-split segment. |
| `prerequisites` | `seg:prerequisiteNote` | literal | Values are free text, not segment IDs, so `dcterms:requires` (which points to a resource) is not used. |
| `L1_codes` | `dcterms:subject` | literal | Top-level codebook category. Kept as text until the codebook is published as a SKOS vocabulary. |
| `annotation_date` | `seg:annotatedOn` | `xsd:date` | When the record was annotated, not when the conversation happened. |
| `annotator` | `seg:annotator` | literal | |
| `text` | — | — | Not converted: conversation content. |
| `title` | — | — | Not converted: free text that may contain personal information. |
| `notes` | — | — | Not converted: free text that may contain personal information. |

## Notes

1. Why not `tf:hasDecisionStatus` from the TalentFlow ontology: its domain is `tf:Decision`, so a reasoner would classify every segment as a TalentFlow decision. `seg:hasDecisionStatus` points to the same SKOS vocabulary without that side effect.
2. Conversation numbering: other files from the same experiment may number conversations from 001 instead of 000. Within this JSON, `000_000` exists, so prefixes start at 000. Before joining with any other file, check one known pair first.
3. The experiment JSON has 11 of these fields. Missing fields are skipped and logged. The public repository uses fictional sample data only; real annotation data never leaves the local machine.
