# Current state
Foundation merged through PR #21 on 2026-10-10; not a v0.1 product release.
Existing main contained README, Apache-2.0 LICENSE and Python .gitignore; license and ignore file
are preserved. No unrelated project code or private materials were imported.

Implemented: original synthetic procurement fixture; offline Python CLI; deterministic single-bid
Evidence Passport JSON output; strict demo count/identity checks; JSON Schema; meaningful smoke,
provenance and CLI tests; documentation, governance, source assessment, CI and templates.

Implemented for issue #5: [37 synthetic edge cases](SYNTHETIC_EDGE_CASES.md), exact expected
assessments/errors, CLI rerun/schema/lineage tests, and conservative optional demo guards for
cancelled awards, duplicate releases and joint suppliers. Counts remain separate; UTC durations
are diagnostic only.

Implemented for issue #11: [canonical v1 tables](DATA_MODEL.md), stable scoped identities,
release/snapshot history, exact decimal amounts, explicit unknown states, relationship validation
and conservative award totals. This is an offline OCDS-shaped subset, tested with invented data;
full source mapping, database storage and live ingestion remain unimplemented.

Planned: all live connectors, canonical real-source validation, three production indicators,
real-source analytical processing, real-data search, CSV exports, graph/R/cyber modules and hosting.
No donation account or FUNDING.yml. Branding remains provisional with known conflicts.
DNCP activation remains gated by open #6/#7. PR #27 proposes a fuller local input contract;
its reviewed files are explicitly incorporated by the stratified-quality follow-up. No automatic
source intake is activated.

The docs/product-roadmap branch expands the README into a proposed long-term product blueprint:
six detailed modules, public/local/research workflows, shared capabilities, dependencies, v0.6
Studio integration and v0.7 hardening milestones, and a v1.0 completion checklist. ROADMAP.md
is aligned with that direction. These documentation changes implement no additional application
features; later-stage capabilities remain planned and exploratory features are separated.

Verification and GitHub issue links are recorded in VALIDATION.md and BACKLOG.md. Next task:
source rights/fields assessment, then a bounded, local DNCP connector with synthetic mapping tests.

Implemented locally for #7: [bounded DNCP gzip intake](DNCP_LOCAL_IMPORT.md), using PR #29
canonical mapping. This supersedes the earlier planned local-intake status only. A limited 22-row source-prefix compatibility check is now recorded below; no representative
pilot, production activation or redistribution clearance; #6 remains open.

DNCP local publication now uses an atomic Linux no-replace directory rename; unsupported
platforms/filesystems fail closed. Fault injection, concurrent writers and SIGKILL boundaries
are covered with synthetic inputs. See [guarantees and recovery](DNCP_PUBLICATION.md).

Implemented for the measured-workload portion of #1: [deterministic offline DNCP benchmarks](DNCP_BENCHMARK.md)
with fresh-process RSS and separate Python-allocation passes, exact/over input boundaries,
dense child graphs, negative inputs and retained environment/hash/measurement records.
[ADR 0002](adr/0002-measured-dncp-workload-budgets.md) leaves input ceilings unchanged. The CLI
now requires operator-configured logical output-byte and file-count ceilings and checks available
space/inodes before and during work; these checks do not replace filesystem quotas or OS limits.
Browser intake remains unimplemented. Measurements and resource tests use synthetic inputs, not a
real-source pilot or production budget certification.

Implemented for part of #6: [deterministic stratified quality assessment](DNCP_QUALITY.md) over
private importer raw evidence, with status/UTC tender-period/lot strata, missing-field states,
bidder/bid/lot diagnostics and explicit screening criteria. The [bounded source check](evidence/dncp-quality-2026-10-30/README.md)
reconfirmed the same 22 prefix records using 256 KiB; no older cases or usable bid-to-lot links
were established. All real analytical indicators remain blocked pending broader frame and
publisher-semantic evidence. Synthetic tests establish algorithm behavior, not source representativeness.

Implemented locally for #10/#12: [versioned Parquet snapshots](PARQUET_SNAPSHOTS.md) and
[isolated synthetic DuckDB cohorts](DUCKDB_COHORTS.md), stacked on draft PR #35. The latter
reuses the verified six-table contract, requires a pinned invented snapshot, and returns exact
currency/UTC-release-period/process-status diagnostics with exclusions. Disposable workers deny
network syscalls, disable engine external access/extensions and enforce OS/resource budgets.
No arbitrary SQL, latest-version inference, FX or real analytical indicators. Source quality,
semantic validation, privacy/rights approval and integration of the draft chain remain open.

Implemented on the draft chain for #3: [local accessible synthetic explorer](FRONTEND_EXPLORER.md)
using React/strict TypeScript/Vite. Five existing invented rows are exported through a pinned,
bounded v1 JSON projection of the original Python record contract, with filters, source/rights/
privacy notes, explicit unknown/zero and loading/error/empty states. No DuckDB/browser bridge,
real-data indicators, accounts, production server or public hosting. #18 remains future work.

## Synthetic provenance extension

Opt-in Evidence Passport 0.2.0 connects the reviewed five-record fixture and its two existing
synthetic findings to exact bytes, original pointers, transformations and a software manifest.
0.1.0 remains accepted, with a lossless incomplete-provenance migration. Snapshot provenance
and versioned cohort diagnostic envelopes replay the importer/writer/query chain against an
explicit snapshot pin. Historical missing environment metadata remains unknown. See
[EVIDENCE_PASSPORT.md](EVIDENCE_PASSPORT.md) for commands and expected results.
The existing frontend is preserved; real analytical indicators remain disabled.
