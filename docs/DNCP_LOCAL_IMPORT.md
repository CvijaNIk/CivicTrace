# Bounded DNCP local import — implementation v1

This change implements an offline subset of #7 on PR #29's canonical model. It does not close
#6, approve redistribution, download data, publish records or activate production indicators.
The pinned design reference is PR #27 (`415bda798e75f478cb06246a0efc0b744b922fc1`), especially
its `docs/DNCP_CONNECTOR_INPUT_CONTRACT.md` and source review. Those research files are not
silently incorporated into this branch. No actual annual dataset was supplied or imported.

## Operation

Run from an installed checkout, with a new output path on a private local filesystem:

```sh
python -m civictrace.dncp /private/cohort.jsonl.gz /private/intake \
  --manifest /private/manifest.json \
  --max-output-bytes "$MAX_OUTPUT_BYTES" \
  --max-output-files "$MAX_OUTPUT_FILES" \
  --min-free-bytes "$MIN_FREE_BYTES" \
  --min-free-inodes "$MIN_FREE_INODES"
```

Only regular, nonsymlink local `.jsonl.gz` inputs are accepted. No URLs, pipes, attachments or
archive members are fetched. Parent directories must already exist. Output is a private 0700
directory; keep it outside git, CI uploads, served directories and cloud publishing. Files inherit
the directory protection. Access control, retention, disk quotas and backups remain the operator's
responsibility. Output disk usage can exceed input size because source, raw rows and models are
retained. The CLI requires explicit per-import application ceilings for logical output bytes and
regular-file count, plus optional free-byte and free-inode safety floors. Choose values for the
specific workload, filesystem and required headroom. The benchmark's recommendation of 12 GiB
free space and 120,000 free inodes provisions that experiment only; it is not a universal importer
limit. No throughput or hard OS RSS ceiling is claimed.

The manifest must explicitly contain these nonempty fields:
`adapter_version` (pin the reviewed code commit), `publisher` (`DNCP`), `intermediary`,
`publication_id` (`63`), `source_url`, `resolved_url`, `snapshot_version`, `partition`,
`retrieved_at` (timezone-bearing acquisition timestamp), `compressed_sha256`, `expanded_sha256`,
`selection` (parent hashes, extraction recipe, expected cohort/row count and exclusions),
`license_id` (`CC-BY-4.0`), `license_url`, `terms_evidence` (exact publisher and registry evidence
URLs, observation times and hashes), `attribution`, `changes`, `exclusions`, `privacy_review`,
`registry_unknown_reason` (use `not-applicable` if registry timestamp is known).
Set `contract_version` to `dncp-local/1`, `redistribution_decision` to `local-only`,
`access_review` to `confirmed`; supply `registry_retrieved_at` as an actual timestamp or null.
Source URLs are provenance labels, never fetched. Free-text evidence is an operator attestation,
not an automated legal review. Do not assert confirmation without reviewed evidence. The adapter
validates presence, selected constants, timestamps and hashes, not authenticity of that evidence.
The complete manifest is preserved alongside output, rather than copied onto every child row.

## Limits and failure behavior

Hard ceilings (API `Limits` may only lower them): 256 MiB compressed, 2 GiB expanded,
50,000 rows, 2 MiB per line including newline, depth 32, expansion ratio 200:1 against complete
compressed size, 128 characters per numeric literal, 4096 characters per required identity.
Decompression produces at most 64 KiB at a time and never materializes the whole expanded file.
JSON parsing/model creation scales with one bounded row. Duplicate tracking retains only SHA-256
OCID digests up to the row ceiling. Python object overhead is greater than raw row bytes; deployment
requiring a hard process memory ceiling should use an OS-limited worker. A synthetic tracemalloc
regression checks the 2000-row path below 16 MiB; it is not a universal RSS guarantee.

`OutputBudget` is mandatory for library callers. `max_bytes` counts the logical contents of every
regular file in the staging output: the compressed source snapshot, validation report, raw rows,
canonical records, manifest and summary. `max_files` counts those regular files, not directories
or filesystem metadata. Both are checked before each file or byte write; crossing either limit
aborts the import. Before staging and during writes, the importer reads `statvfs` available bytes
and free inode counts and preserves the configured `min_free_bytes` and `min_free_inodes` floors.
These are observations, not reservations shared between concurrent importers. Filesystem quotas,
container limits and other writers may expose less capacity than `statvfs` reports; the actual
filesystem remains authoritative and `ENOSPC`/`EDQUOT` failures abort and clean staging. Logical
bytes are not allocated blocks, physical device usage, inode metadata or a power-loss guarantee.

The complete compressed snapshot is copied and hash-verified before parsing. Full gzip EOF/CRC,
expanded hash, limits and single-member framing are required. Truncation, concatenated members,
trailing garbage and limit failures discard staging; no canonical directory is published.
Publication and recovery now follow [the atomic publication contract](DNCP_PUBLICATION.md).
On supported Linux local filesystems a single `renameat2(RENAME_NOREPLACE)` publishes the
entire closed staging directory, including summary and manifest. Existing entries are never
replaced, including empty directories and dangling symlinks. Other platforms, missing libc/kernel
support or filesystem refusal fail closed; there is no per-file or check-then-rename fallback.
A handled SIGINT/SIGTERM or ordinary failure removes private `.dncp-*` staging before exit. An
uncatchable SIGKILL, host crash, or failed cleanup can leave a mode-0700 private staging directory,
never a partial final output; inspect and remove abandoned staging manually after confirming no
import process is using it.
There is no resume mode. Parent directories must be private, nonsymlink and stable during import.
This guarantees atomic visibility for process failures, not durability against power loss.

Each physical line has a SHA-256 and original ordinal and is retained byte-for-byte as `.raw`,
including invalid UTF-8/JSON. `validation.jsonl` reports accepted/rejected rows, field states and
child quarantine pointers. Duplicate keys, nonfinite constants, excessive nesting, invalid
encoding/shape/identity reject a row. Duplicate OCIDs reject later rows, deterministically in file
order. Missing child IDs/values or dangling links quarantine that child; the original release
remains intact in the canonical source record and raw evidence. Other structural errors can reject
the entire row. This is conservative intake, not a full OCDS validator or complete child salvage.

## Mapping and interpretation

Per-row canonical JSON uses existing process/release/party/award/contract and award-supplier tables.
Snapshot/row SHA-256, source URL, acquisition timestamp, code version and original child pointers
provide lineage. All byte-identical inputs and manifest/limits yield byte-identical output files.
Decimal JSON numbers use Decimal, never floats. Original offsets and UTC date values are retained.
Missing fields remain absent/null, not zero. Tender value, IDs, methods, lots and bid extensions stay
in the preserved source record; this version does not promote them into new canonical columns.
The normalizer's five-currency subset remains explicit; invalid/unsupported money stays in field
states and is excluded by canonical total calculations. Signing dates are never imputed.
Reported tenderers never become bid counts; joint awards are not allocated to suppliers; contracts
are not added to award spending. This adapter emits no irregularity findings or demo Evidence
Passports. It does not infer latest versions or merge snapshots.

## Open #6 gates and verification

Before any real local pilot: obtain an appropriately bounded user-supplied file; review acquisition
rights, exact artifact terms, attribution and personal-data handling; record hashes, reviewed scope
and evidence in the manifest. The 22-record review in PR #27 was a nonrepresentative prefix, not
approval for every year or artifact. No real-data validation report is claimed here.

Still unconfirmed: tenderer vs bid/lot semantics; representative completeness by year/stage;
missing child identity and signing-date policy with the publisher; extensions; compilation and
partition rules; current terms for the actual supplied snapshot. #6 stays open. Public extracts,
production activation and legal clearance require separate review. #7's real-data acceptance gate
also remains open until that controlled pilot is actually performed.

Tests use invented organizations only: gzip integrity/framing, exact and exceeded limits, ratio,
JSON ambiguity/encoding/depth/numbers, child quarantine, duplicate OCIDs, timezone preservation,
exact large amounts, missing signing date/counts, deterministic full-directory output and memory
regression. All 37 existing synthetic cases remain in the full suite.

Reproduce entirely offline from the checkout:

```sh
python -m pip install -e '.[dev]'
python -m pytest tests/test_dncp.py -q
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python scripts/check_docs.py
```

`test_reproducible_mapping` creates an invented compiled release and explicit synthetic manifest,
imports it twice and compares every output byte. Expected: one accepted row, two suppliers on one
award, PYG `9007199254740993.01`, unknown bid count/signing date, UTC midnight for the supplied
`+02:00` timestamp. `test_rejects_and_quarantine` expects 1 accepted and 3 rejected rows and retains
the parent with a missing-ID contract quarantined. No rights to an actual dataset are implied by
these synthetic attestations.

## Resource measurements

The 2,000-row `tracemalloc` regression is not a process RSS guarantee. The separate
[reproducible synthetic resource experiment](DNCP_BENCHMARK.md) covers fresh-process RSS,
Python allocations, throughput, disk/file amplification and independent input boundaries.
See [ADR 0002](adr/0002-measured-dncp-workload-budgets.md) before interpreting these observations
as workload budgets. The configured logical output budget is application-enforced; no OS-enforced
RSS or disk quota is installed by the importer.
