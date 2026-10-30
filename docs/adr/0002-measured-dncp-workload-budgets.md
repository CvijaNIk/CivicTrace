# ADR 0002: measured local DNCP workload budgets

Status: accepted for the offline experimental importer, 2026-10-29. Related issue: #1.
This is not real-data approval, a browser implementation or a memory safety certification.

## Decision and boundaries

Keep the local streaming gzip/JSONL CLI and its existing hard input ceilings:
256 MiB compressed, 2 GiB expanded, 50,000 rows, 2 MiB per line, depth 32,
and expansion ratio 200. Limits may be lowered, never raised through `Limits`.
The byte limits constrain input, not RSS, output amplification or available disk.
The row ceiling bounds retained hashed OCIDs; a single row's child/model graph still matters.
No production memory guarantee follows from an empirical maximum.

Browser DNCP intake has an operational budget of zero: it is unimplemented. Do not upload
private files to a public site or infer a browser memory allowance from the Python measurements.
The future browser must obtain separate worker/cancellation/heap measurements before activation.
Demo JSON and DNCP JSONL are different contracts; the former's limits cannot be transferred.

Use [the offline experiment](../DNCP_BENCHMARK.md) and its versioned raw observations before
changing ceilings. An operator must now supply a per-import logical output-byte ceiling and regular
file-count ceiling, and may configure free-byte/free-inode safety floors. They are explicit
application budgets, not defaults inferred from the single benchmark host. `statvfs` is checked
before staging and during writes; these checks are observations, not cross-process reservations.
Filesystem quotas and concurrent external writers can expose less capacity, so actual writes may
still fail with `ENOSPC` or `EDQUOT`; those failures abort and clean staging. The benchmark's
12 GiB / 120,000 inode provisioning suggestion is specific to its suite and not a universal cap.
These output controls do not establish safety for every legal JSON shape or an OS-enforced memory
limit. Deployments requiring hard memory or disk isolation still need OS/container limits.

## Architecture and alternatives

Streaming one line/model at a time preserves exact raw evidence, canonical field states,
source hashes and original pointers. Hashed duplicate tracking grows with accepted identities.
The importer writes separate raw/model files; this favors inspection and crash recovery but
amplifies disk space and inode consumption. `OutputBudget` checks prospective logical bytes and
file count before writes, while available bytes and free inodes are observed through `statvfs`.
Neither count includes directory metadata or promises physical-block accounting. Publication
remains the single Linux atomic
no-replace rename from PR #31; no benchmark replaces it with a weaker operation.

Rejected for now: loading the annual JSON into memory; an implicit browser upload; a hosted
benchmark service; automatic DNCP downloads. These conflict with bounded/local processing or
privacy. Database-backed duplicate tracking, batched evidence containers and incremental
canonical serialization could reduce memory/filesystem costs, but need independent integrity,
provenance and crash-recovery tests before replacing the current contract. Polars/DuckDB do
not automatically bound the Python graph created for a single row.

## Evidence and interpretation

The generator uses only explicitly invented identifiers, deterministic SHAKE padding and gzip
mtime zero. Its manifest uses a synthetic URN and synthetic rights/review annotations; satisfying
the import manifest schema is not evidence that a real publisher supplied these bytes.
Unknown values remain unknown; missing child values are quarantined, not imputed to zero.

Small/medium, maximum unique row count, dense child graphs, exact/over line and byte ceilings,
malformed JSON, missing values, corrupt gzip and expansion-ratio rejection are measured.
Expected summaries, absence of partial publication and cleanup are asserted by the harness.
Existing provenance and SIGKILL/concurrent publication regressions remain mandatory.
See [method, commands and results](../DNCP_BENCHMARK.md), including explicit non-guarantees.
