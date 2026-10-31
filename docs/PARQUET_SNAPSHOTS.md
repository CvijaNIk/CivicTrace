# Local versioned Parquet snapshots

Implemented contract: `civictrace-parquet/1`, canonical `civictrace-canonical/1`.
This is a local storage projection, not a reviewed analytical cohort. Every manifest carries
`analytics_enabled: false`. No rule, indicator, public export or DuckDB query layer is activated.

## Dependency review, 2026-10-31

Reviewed all remote branches and open/closed PRs before implementation. No existing Parquet writer
was present. This branch stacks directly on #34 (`e1c65b82d96d7ac9e37e22efd02922b10fce03b6`),
which includes #29–#33; none of those PRs was merged by this work.

| Issue | Existing implementation reused | Remaining boundary |
| --- | --- | --- |
| #7 | #30 importer, #31 atomic publication, #32 measurements, #33 output budgets | Local compiled DNCP subset only |
| #8 | Canonical typed field states, importer quarantine/validation, #34 stratified quality | Broader source quality/semantics unconfirmed |
| #9 | #29 scoped/versioned identities and explicit release selection; importer rejects repeated OCIDs | General amendment reconciliation, conflicting duplicates and cross-source identity resolution are not complete |
| #10 | This snapshot writer, verifier and synthetic example | Review and larger-workload compaction remain |
| #11 | #29 six canonical tables, decimals, UTC dates and null states | Mapping intentionally limited; no guessed field meanings |
| #12 | No implementation in this increment | Read-only isolated analytical layer still depends on reviewed #10/#11 |

Issue #9 is only partially implemented. This writer retains the importer's duplicate rejects and
all imported versions; it never manufactures a latest-release view or claims full #9 completion.

## Reproduce

Linux is required for the reused atomic `renameat2(RENAME_NOREPLACE)` primitive. Unsupported
platforms/filesystems fail closed. Install from this branch with Python 3.11–3.13:

```sh
python -m pip install -e '.[dev,snapshots]'
python scripts/snapshot_example.py /tmp/invented-snapshots --rows 100
python -m pytest tests/test_snapshots.py -q
```

The example invents every record and all acquisition metadata, including license/review labels.
Those synthetic labels do not clear any actual source rights. It writes two new private snapshots,
asserts identical manifests and byte inventories, and prints snapshot identity and resource metrics.
The directory must not already exist. No network request occurs.

To convert an existing operator-controlled private intake directory:

```sh
python -m civictrace.snapshots /private/intake /private/snapshot-v1 \
  --max-bytes 1073741824 --max-files 100000 \
  --min-free-bytes 1073741824 --min-free-inodes 10000
python -c 'from civictrace.snapshots import verify_snapshot; verify_snapshot("/private/snapshot-v1")'
```

The CLI requires explicit logical byte/file budgets. Keep these below actual available disk/inodes
with safety floors for filesystem allocation and directories. Rights/privacy decisions from the
source manifest remain binding. Snapshots contain original records and must stay private.

## Layout and types

`evidence/` contains the entire replayed importer output: original compressed artifact, exact raw
rows, source manifest, summary, validation JSONL, and canonical JSON per accepted row. Its complete
byte inventory must equal the supplied intake. A bounded importer replay checks compressed and
expanded hashes, row ordering, identity rejection, original pointers, field states and quarantines.
Changing the canonical JSON or validation report alone cannot silently change the Parquet view.
Replay uses the exact importer limits recorded in the summary; changed connector behavior fails
closed. Preserve old code/environment to rebuild old snapshots.

`tables/<table>/release_year=<year|unknown>/<ordinal>-<raw-hash>.parquet` contains six tables:
processes, releases, parties, awards, contracts and award_suppliers. Year comes from the release's
UTC timestamp, including for children; it is not the award year, financial year or source partition.
Invalid/missing release dates use `unknown`. Cancelled processes are retained. No currency or stage
cohort is inferred. The source's own partition/selection remain verbatim in the source manifest.

Each file uses the explicit Arrow schema in `schema.arrow`, also embedded in every Parquet footer.
Empty tables are declared with count zero and the schema remains available; no placeholder rows.
Columns include scoped identity/linkage, source record hash and canonical filename, date, status,
currency, amount and field states. `canonical_json` preserves the full canonical row, including
source schemes, null/absent/invalid states, pointers and exact normalized decimal strings. Resolve
`source_file` relative to `evidence/`; join its provenance to the exact raw record and compressed
artifact. Child IDs can repeat across release versions: retain `release_id` in identity joins.

Dates use `timestamp[us, UTC]`. Monetary projection uses `decimal256(76,18)` without floats or
rounding; zero and values above binary64's exact-integer range stay exact. Canonical amounts too
large or too fractional for this type remain in canonical JSON and raw evidence, with a null typed
amount and `projection_exclusion=amount_outside_decimal256_76_18`. This excludes only the typed
projection, not the original record. Invalid amounts and unsupported currencies keep their original
field states and null projections; currencies are never converted. Do not aggregate null/excluded
amounts or combine currencies without an explicitly reviewed policy.

`evidence/validation.jsonl` is the rejection/quarantine/field-state ledger. The manifest records
source/connector/schema versions, retrieval timestamp, selection, source rights and privacy metadata,
validation state counts, per-table counts and projection exclusion count. Each row records its own
projection exclusion. All data files, schema and evidence have exact byte lengths and SHA-256 hashes.
`manifest.sha256` covers manifest bytes. `snapshot_id` hashes canonical manifest JSON before adding
that ID; writer version, source metadata and configured budgets are part of this identity. No wall
clock creation time or random staging name enters snapshot content. The retrieval time is preserved
as asserted by the caller; it is not independently authenticated.

PyArrow 23.0.1 is pinned for byte reproducibility. A future writer/schema change needs a new contract
or an explicitly reviewed compatibility decision. Hashes establish byte identity, not publisher
truth or authenticity; retain an independently trusted snapshot ID/hash when detecting coordinated
modification matters. The verifier checks the complete inventory and manifest identity, not source
semantics or an external signature.

## Publication, recovery and resource boundaries

Files are written beneath a mode-0700 sibling `.parquet-*` directory. Each Arrow output write checks
logical bytes, file count and filesystem free-space/inode floors before writing. No entire Parquet
file is buffered. All files close, inventory verifies and files/directories fsync before a single
atomic no-replace rename; the parent directory is then fsynced. Existing paths, dangling symlinks
and a destination created by a concurrent writer are never replaced. Operator control of all input
and output parent directories is required; this is not a sandbox against a hostile concurrent owner.

Handled failures clean staging. SIGKILL/power loss may leave private staging. Stop writers, inspect
and remove that specific staging directory manually; never rename it into place. Retry into an
absent final path. If parent fsync fails after rename, final visibility has already changed: verify
the final path before deciding recovery. Filesystem/hardware crash durability remains platform
specific. No claim of universal power-loss protection is made.

Input ceilings come from the existing importer (up to 256 MiB gzip, 2 GiB expanded, 50,000 rows,
2 MiB line). A canonical model is additionally limited to 64 MiB, metadata to 32 MiB, inventory to
400,000 files. A snapshot can reject a valid intake if projection/manifest budgets are exceeded.
The example layout deliberately writes one file per nonempty table per model; at high row counts,
small-file and manifest overhead can hit ceilings before importer limits. There is no claim that a
50,000-row maximum importer run always fits this snapshot format. Future compaction needs its own
reproducibility tests; do not remove these limits to accommodate a large source.

Memory scales with one bounded model and its Arrow table, plus bounded inventory/manifest metadata.
The importer replay also temporarily duplicates local evidence on disk. Native Arrow allocation is
not an OS memory cap. Logical bytes differ from allocated disk; directories and filesystem overhead
require additional inode/space headroom. Free-space checks cannot reserve disk against other users.
Use OS resource enforcement externally where a strict RSS/CPU ceiling is needed.

## Synthetic measurements and validation

Python 3.12.14, PyArrow 23.0.1, Linux; two snapshots per run, exact inventories equal:

| Invented source rows | First snapshot seconds | Process peak RSS KiB | Logical snapshot bytes | Allocated bytes including directories | Files | Directories |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 1.557 | 112964 | 6794259 | 8691712 | 807 | 14 |
| 1000 | 13.150 | 136388 | 67902310 | 85950464 | 8007 | 14 |

RSS includes interpreter, Arrow imports, intake, both builds and verification. Timings are local
observations, not performance guarantees, maximum-input measurements or a proven memory ceiling.
Re-run the example in a fresh process for each row count; paths/timing/filesystem can vary.

Tests cover deterministic replay, full source preservation, manifest/data corruption, timezone
partition boundaries, cancelled releases, empty sources, child quarantine, duplicate processes,
invalid/unsupported values, decimal limits, logical/free-resource limits, mid-write errors,
publication races, SIGKILL during Parquet writing, preserved prior snapshots and recovery by retry.
No actual source records are fixtures. Real analytics remains blocked by the #34 quality gate.

Local final verification: Python 3.12.14, 143 tests and 95 subtests passed (32 snapshot tests).
Ruff 0.17.3 lint/format, relative-document links, whitespace checks and the unchanged deterministic
synthetic CLI demo passed. The snapshot module CLI reproduced the 100-row example snapshot ID.
Hosted Python 3.11/3.12/3.13 verification is separate; see the PR's Actions status for its exact head.
