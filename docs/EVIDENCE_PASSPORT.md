# Versioned Evidence Passport
Machine contract: [JSON Schema](../schemas/evidence-passport.schema.json), Draft 2020-12.
The legacy 0.1.0 fields remain required; unknown original-file hash can be null with an explicit limitation.
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
The opt-in 0.2.0 extension below adds environment, rights and transformation fingerprints.
General production exports and historical environment reconstruction remain outside this scope.

## Implemented 0.2.0 provenance (synthetic only)

The dispatch schema accepts unchanged 0.1.0 passports and the opt-in 0.2.0 contract.
Frozen version schemas are retained alongside it. `migrate_passport` preserves IDs, facts,
rights and all original fields, adds `legacy-incomplete` provenance and leaves unavailable
expanded hashes, pointers, rights evidence and historical environment null. Migration is
idempotent; it does not certify completeness. Existing CLI calls still emit 0.1.0.

### Inventory reviewed before this extension

| Existing component | Already preserved | New connection |
| --- | --- | --- |
| DNCP local importer | Original gzip, compressed/expanded SHA-256, raw line hash/ordinal, original child pointers, collection timestamp, rights/registry/source manifest, quarantine ledger | Snapshot provenance resolver exposes these per source row |
| Canonical model | Scoped process/release/entity identities, source values and typed unknown states | Entity identity map connects projected rows to canonical file and original raw row |
| Parquet snapshot | Source evidence inventory, per-file hashes, snapshot ID, original/canonical records, writer version, Arrow schema, deterministic importer replay | Independent snapshot pin plus complete importer/writer replay before provenance export |
| Existing evidence demo | Original-file hash, source ID, rule version and asserted collection time | Opt-in 0.2.0 adds JSON pointer, expanded hash, transformation inputs/outputs and implementation hashes, current software environment and source restrictions |
| React explorer | Five reviewed synthetic records and fixture pin | Separate bundle keys passports by the existing record IDs; frontend payload and UI are unchanged |

### Reproduce the complete fixture chain

```sh
python -m pip install -e '.[dev]'
python scripts/lineage_example.py
python scripts/lineage_example.py --output /tmp/synthetic-passports.json
civictrace examples/synthetic_procurement.json --collected-at 2026-10-10T00:00:00Z --lineage --output /tmp/findings-v2.json
python -m pytest tests/test_lineage.py -q
```

Expected first command output: `results: 5`, `findings: 2`, `integrity_verified: true`,
`source_truth_verified: false`, `acquisition_time_authenticated: false`,
`analytics_enabled: false`. The bundle has seven entries: five original explorer records
and the two existing demo findings (SYN-001 and SYN-005). It is a local sidecar; no new
browser data loading or public export is activated. Both export commands refuse overwrite.
The fixture is uncompressed: its original and expanded hashes intentionally match.
JSON pointers `/0` through `/4` refer to the original array. Record hashes cover explicitly
serialized JSON, not an invented original-record byte substring. Original full-file bytes
remain the byte-exact anchor. Source publication dates remain null; supplied collection
metadata is an assertion, not an externally authenticated timestamp.

`verify_fixture_passports` regenerates all records, pointers, transformations and outputs
against the independently pinned fixture, and compares the entire bundle. Determinism holds
for identical input, timestamp, implementation and environment. An environment change is a
review event, not silently ignored. Keep old code and environment to verify old bundles.

### Reproduce snapshot and cohort provenance

```sh
python scripts/analytics_example.py /tmp/invented-lineage
python - <<'PY'
from civictrace.analytics import Cohort, query_snapshot
from civictrace.lineage import cohort_result_passport
from civictrace.snapshots import verify_snapshot
p = '/tmp/invented-lineage/snapshot-a'
# Trusted here only because the preceding script just generated this synthetic snapshot.
pin = verify_snapshot(p)['snapshot_id']
c = Cohort('PYG', '2026-01-01T00:00:00Z', '2027-01-01T00:00:00Z', 'complete')
r = query_snapshot(p, expected_snapshot_id=pin, cohort=c)
e = cohort_result_passport(p, r, expected_snapshot_id=pin)
assert len(e['lineage']['rows']) == 3
assert e['result']['exact_amount_sum'] == '27021597764222979.030000000000000000'
assert e['result']['analytics_enabled'] is False
print('3 source rows; original gzip -> raw rows -> canonical -> Parquet -> cohort verified')
PY
```

The versioned `civictrace-cohort-passport/1` envelope contains the unchanged cohort diagnostic,
source manifest, complete byte inventory, canonical-file and entity references, raw row hashes,
source dates with their field states, collection date, rights and registry metadata. Its last
transformation records cohort parameters, query version, implementation hash and exact output
hash. The whole fixed query is rerun before accepting a supplied result. The input scope is
explicitly **all imported source rows, including excluded rows**, not a claim that every row
contributed to a sum. Follow original line ordinal plus raw filename and child pointer; entity
identities alone do not select a release version.

Existing snapshots are unchanged: they did not record a complete historical environment.
Their writer version remains available; the new environment describes **verification time**.
Full historical environment remains unknown. The resolver reconstructs the snapshot using
recorded budgets and limits and compares the full manifest; a changed implementation that
produces different bytes fails closed. Source manifests and raw evidence remain local-only.
Snapshot replay uses the existing importer/writer resource limits, Linux publication primitive,
and operator-controlled directories; it is not a hostile-filesystem sandbox.

Cryptographic integrity does not establish source truth, actual collection time, authenticity,
legal admissibility, or permitted redistribution. A trusted out-of-band pin is needed to detect
coordinated replacement of bytes and their hashes. Synthetic metadata labels are guards, not
proof of origin or rights clearance. Real source semantics and analytical indicators remain
blocked. No registry enrichment or real rights approval is inferred from a synthetic example.

## Synthetic finding presentation

The existing React application now includes an opt-in `/?view=passport` view for
legacy, migrated-incomplete and complete synthetic findings. See
[PASSPORT_VIEW.md](PASSPORT_VIEW.md) for contracts, security boundaries and reproduction.
Limitations stay expanded; hashes are not proof of truth. Real analytics remain disabled.
