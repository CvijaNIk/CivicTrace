# Evidence Passport 0.1.0
Machine contract: [JSON Schema](../schemas/evidence-passport.schema.json), Draft 2020-12.
Every schema field is required; unknown original-file hash can be null with an explicit limitation.
Validators must enable date-time format checking. The demo produces known hashes only.

| Group | Human-readable presentation |
| --- | --- |
| finding_id/schema_version | Stable identifier and schema version |
| source | Publisher, source URL or local reference, timezone-aware collection time, original record ID, original-file hash, snapshot version, license |
| rule | Rule ID and methodology version |
| facts | Directly reported identity facts, distinguished from inference |
| computation | Expression, parameters and observed result |
| benchmark | Explicit comparator and value, or documented absence |
| limitations/uncertainty | Missing inputs, quality concerns, sampling limits; no arbitrary probability |
| interpretation | Analyst meaning, separated from factual observations |
| allegations | Explicitly separate contested claims; empty in all demonstrations |
| verification_steps | Source checks, alternative explanations, corroboration |

Render in this order, visibly marking synthetic records. Escape every source-provided string and
allow only safe hyperlink schemes. Future reports must not hide limitations behind collapsed UI.
Evidence export is deterministic given ordered records, snapshot bytes and an explicit collection
timestamp. Demo finding IDs hash snapshot + record ID + rule/version. Input order determines
output order; sorting and canonical production identity remain backlog tasks.
SHA-256 verifies unchanged bytes, not source truth, timestamp authenticity or evidentiary admissibility.
A future export manifest should include software commit, environment, licenses and chain of
transformations. Schema changes require migration examples and compatibility tests.
