# Evidence index

- `requests.json`: observed request metadata; page bodies are not bundled. SHA-256 identifies the
  bytes observed but is not a substitute for an archive or proof of unchanged future terms.
- `profile.json`: research observations of the 22 complete lines within a 256 KiB gzip prefix.
  `full_snapshot_sha256` is intentionally null; `compressed_prefix_sha256` covers only that prefix.
  Raw records and the incomplete final line are not published.

Attribution for source-derived OCIDs and field observations: Dirección Nacional de Contrataciones
Públicas (DNCP), Paraguay, via Open Contracting Partnership Data Registry publication 63,
[exact version 4097 annual 2025 artifact](https://fastly.data.open-contracting.org/downloads/paraguay_dncp_records/4097/2025.jsonl.gz),
retrieved 2026-10-28; artifact Last-Modified 2026-08-20, as observed in the response.
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), based on publisher catalogue and registry
licensing evidence linked in the [review](../../DNCP_SOURCE_REVIEW_2026_10_28.md).

Changes: OCP's compiled-release representation is inherited; CivicTrace selects complete prefix
lines, hashes them and replaces source content with field-state observations. No source amounts,
names, titles or contacts are reproduced. DNCP disclaims accuracy and freshness and places reuse
responsibility on the user. No endorsement by DNCP or OCP. This source attribution is separate
from Apache-2.0 for original project code, documentation and synthetic test material.

Local validation on Python 3.12.14: pytest 9.2.0 — 11 tests passed, 11 subtests passed;
ruff 0.17.3 lint/format passed; relative-document links passed; existing synthetic CLI output and
offline prefix-profile reruns were byte-identical. Committed `records` match the offline rerun.
Python 3.11/3.13 and exact candidate hosted CI must be checked separately; results from PR #26
are not inherited by this change. No network tests are run by CI.
