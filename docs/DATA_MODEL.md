# Canonical procurement model v1

Implemented in `backend/src/civictrace/canonical.py`, schema `civictrace-canonical/1`.
This is a deterministic offline in-memory table model and OCDS-shaped subset mapper.
It does not implement a DNCP connector, database migration or complete OCDS validation.

| Table | Identity and relations |
| --- | --- |
| processes | SHA-256 of length-safe JSON tuple (process, exact OCID); no name matching |
| releases | Process + exact release ID + snapshot hash; separate source date, status, provenance and preserved source record |
| parties | Stable process-local party ID; row version is (release_id, id); retain source identifiers, schemes, roles and jurisdiction without merging names |
| awards | Stable process-local award ID; row version is (release_id, id); status, event date and exact money |
| contracts | Stable process-local contract ID; row version is (release_id, id); award_id must reference an award in the same release |
| award_suppliers | Unique (release_id, award_id, party_id); party must exist in the same release |

All child rows carry process_id and release_id. Their provenance is reached through release_id.
Duplicate releases, parties, awards, contracts or supplier links fail atomically. Repeating a
release ID in another snapshot creates another version; repeating it in one snapshot is rejected,
even if content is identical. Amendments never overwrite earlier versions. Selection of one
applicable version per process is mandatory for totals; timestamps alone do not establish which
release supersedes another. Input ordering does not affect serialized output.

## Mapping and unknowns

Each mapped scalar carries `state` (present, absent, null, invalid, unsupported), JSON pointer,
normalized value and, when supplied, original raw value. Invalid/unsupported fields carry reasons.
Zero is present. Null and absent stay distinct. Counts exclude bool and negative integers.
`/tender/numberOfTenderers` maps only to reported_tenderer_count. Canonical bid_count stays absent;
neither detail rows nor supplier counts establish the number of offers.

RFC3339 dates require offsets and valid calendars. Original strings remain available beside UTC
values. Submission start/end and award/contract dates are distinct. Reversed submission periods
are flagged; missing dates do not become midnight or a signing date. Money accepts decimal strings,
integers or Decimal objects, rejecting binary floats, bool, negative and nonfinite amounts. The v1
bound is 128 significant digits and exponent magnitude 128. Supported ISO 4217 subset is explicitly
EUR, USD, GBP, PYG and RSD; other currencies are unsupported, never inferred. Exact totals use a
512-digit local Decimal context and never combine currencies or perform implicit FX conversion.

`award_totals` requires one explicitly selected release per process. Only active awards of active
or complete procedures with both amount and supported currency contribute. Unknown/cancelled/
pending/unsuccessful statuses or unknown values exclude the award and return its ID in the coverage
report. A joint award contributes once to the procedure total, regardless of supplier cardinality.
Supplier allocation is explicitly unavailable: no equal split or concentration inference is made.
Contract values are separate and never added to award values as additional spending. Empty totals
with exclusions mean unavailable coverage, not proof of zero spending. No fraud inference is made.

## Provenance, rights and deliberate exclusions

Callers supply snapshot and original-record SHA-256, source reference, collection time, adapter
version, license, attribution and explicit privacy review. The mapper preserves these assertions;
it does not authenticate hashes against source bytes or authorize redistribution. Multiple releases
in one call must belong to that same original source record/package. Raw source records are retained
in the result for lineage; public export/redaction is unimplemented. Use only synthetic inputs here.
Real-data intake remains blocked by #6/#7 and must implement the fuller reviewed manifest contract.

Design reference: [PR #27 proposed DNCP contract](https://github.com/CvijaNIk/CivicTrace/blob/415bda798e75f478cb06246a0efc0b744b922fc1/docs/DNCP_CONNECTOR_INPUT_CONTRACT.md).
This mapper does not accept gzip/files/URLs. Envelope limits, source rights verification, upstream
retrieval timestamps, compiled-release semantics and child quarantine/reject streams belong to #7.
Missing required child identity or dangling linkage fails the batch here; raw data is never silently
assigned a made-up ID. Optional malformed scalar values remain explicit field results.

Lots, bids/details/statistics, tender value, procurement method, amendments metadata and extensions
are retained in source_record but are not normalized into analytical tables in v1. No inferred bid
count, lot allocation, beneficial ownership, FX, public export or automated latest-state resolution.
This is a documented bounded mapping, not a claim of full OCDS or DNCP production readiness.

## Reproduce

From the repository root after installing `.[dev]`:

```sh
PYTHONPATH=backend/src python -m pytest -q tests/test_canonical.py tests/test_synthetic_edges.py
PYTHONPATH=backend/src python scripts/canonical_example.py
```

The example emits exact expected totals `{"EUR": "9007199254740993.01"}` for two joint suppliers
and one contract of the same amount. The amended cancelled award emits empty totals and one
excluded award. It prints the SHA-256 of deterministic canonical bytes. Tests bridge all 37 cases
from PR #28 for counts/periods and retain their original full assessment/CLI regression suite.
