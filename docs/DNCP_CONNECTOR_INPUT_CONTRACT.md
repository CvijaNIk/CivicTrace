# Proposed DNCP local connector input contract (research v1)

Proposal for #7, based on the [2026-10-28 review](DNCP_SOURCE_REVIEW_2026_10_28.md).
No connector, canonical schema migration or analytical indicator is implemented by this document.

## Envelope and provenance

Accept a **user-provided regular local `.jsonl.gz` file**, one flat OCP compiled release per line,
plus an explicit manifest. Do not accept arbitrary URLs, API record packages, archive members,
symlinks, pipes or automatic annual downloads through this adapter. Publisher record packages
need a separately tested adapter; do not guess the shape. No downloads from source document URLs.

Required manifest fields (reject missing values unless marked nullable):

| Field | Contract |
| --- | --- |
| `contract_version`, `adapter_version` | Explicit pinned versions; initially `dncp-local/1` and the reviewed implementation commit. |
| `publisher`, `intermediary`, `publication_id` | DNCP; Open Contracting Partnership; 63. |
| `source_url`, `resolved_url`, `snapshot_version`, `partition` | Exact annual artifact URL and resolved version directory, e.g. 4097 and 2025; never `latest` alone. |
| `retrieved_at`, `registry_retrieved_at` | Separate timezone-bearing timestamps; latter may be null with an explicit unknown reason. Do not substitute CivicTrace time for upstream retrieval time. |
| `compressed_sha256`, `expanded_sha256` | Hash complete bytes in order, not parsed/reserialized JSON. Verify expected compressed hash before normalization; check full gzip EOF/CRC. |
| `selection` | Explicit complete-file/line/OCID/cohort rule, row count and limits; retain original row numbers and raw row SHA-256. |
| `license_id`, `license_url`, `terms_evidence` | CC-BY-4.0, canonical license URL; exact publisher/registry evidence URLs, observed time and hashes. Do not rely on registry site footer alone. |
| `attribution`, `changes`, `exclusions` | Retain upstream notices and OCP compilation lineage; describe every CivicTrace transformation and excluded row/field. |
| `redistribution_decision`, `privacy_review` | Explicit reviewed scope and rationale: local only vs approved minimized extract; unknown rights block distribution. No default public permission. |

Raw files and original lines stay immutable in a local evidence directory outside git, CI artifacts
and hosted outputs. Public analytical exports reference hashes and minimized fields; original
records may contain personal information and need local access/retention controls.

Proposed initial hard ceilings, configurable only downward: 256 MiB compressed, 2 GiB expanded,
50,000 rows, 2 MiB per line, JSON depth 32, numeric literal length 128 and identity length 4096.
These are **unimplemented proposals**, not performance claims. A larger file is rejected; users
must prepare a bounded artifact explicitly, preserving parent hashes and the extraction recipe.
Streaming validation must stop at each limit plus one byte/row without materializing the full file.
Reject invalid UTF-8, duplicate object keys, NaN/Infinity, invalid gzip or trailing/concatenated
members outside the accepted single-member contract. No partial canonical output on fatal failure.

## Record and field rules

A row is one compiled process, with `tag` including `compiled`, an opaque nonempty release `id`,
`ocid` starting `ocds-03ad3f-`, and a `tender` object. OCID identifies the process, not the release,
lot or award. Reject duplicate OCIDs within an artifact rather than silently overwriting. Across
snapshots, version by snapshot hash; do not combine latest states without an explicit merge rule.
Preserve UUIDs, case and OCID suffixes; never coerce identifiers through floating point.

| Source pointer | Proposed canonical handling |
| --- | --- |
| `/ocid`, `/id`, `/tender/id` | Separate process, compiled release and tender identity; raw pointer and line hash on each canonical object. Missing required identity rejects the row with a stable reason code. |
| `/tender/status`, `/tender/procurementMethod`, `/tender/lots` | Preserve source status/method and lot references. Unsupported values receive an explicit validation result; no silent status recode. |
| `/tender/numberOfTenderers` | Nullable `reported_tenderer_count`, nonnegative integer excluding bool; not `bid_count`. Preserve absent vs explicit null vs invalid. No fallback to supplier count or length of tenderers. |
| `/bids/details`, `/bids/statistics` | Preserve detail identity, lot references and statistic measure/scope separately. An absent array is unknown, an empty array is observed empty without a completeness guarantee. Do not derive submissions until coverage, statuses and deduplication semantics are verified. |
| `/date`, `/tender/datePublished`, `/tender/tenderPeriod/startDate`, `/tender/tenderPeriod/endDate` | Separate source/release, publication and submission timestamps. Validate RFC3339 timezone and calendar, preserve original offset/string and UTC representation. Flag reversed periods; no inferred signing dates. |
| `/awards/*/date`, `/contracts/*/dateSigned` | Keep event identity and distinct dates. Missing signing date excludes signing-time indicators, not the whole process. |
| `/tender/value`, `/awards/*/value`, `/contracts/*/value`, `/bids/details/*/value` | Distinct amount/currency pairs using exact decimals; preserve zero, missing and null separately. Validate finite nonnegative amounts and pinned ISO 4217 codes; unsupported/negative values require reasoned quarantine. Never infer PYG, convert FX implicitly or sum different currencies. |
| `/awards/*`, `/contracts/*` | Preserve one-to-many relations and `awardID`; missing child ID/value quarantines that child for affected computations while retaining the parent and raw bytes. Do not add award and contract amounts together as spending. |

Every field result carries `state` (`present`, `absent`, `null`, `invalid`, `unsupported`), source
pointer and reason where applicable. Stable reject categories: envelope/limit/encoding/JSON/identity,
plus child-level date/value/currency/linkage errors. Invalid count never becomes zero. Unknown
inputs exclude only affected indicators, with cohort denominator/exclusion counts recorded.
Output raw-record references, canonical records, immutable manifest and deterministic rejects.
Do not feed `reported_tenderer_count` into the demo `bid_count` interface without a reviewed rule.

## Implementation acceptance gate

Before #7 can claim completion, prove full gzip CRC/hash/row limits with boundary and malformed
synthetic fixtures, expected mapping of one-to-many awards/contracts/lots, missing/invalid states,
duplicate identities, deterministic output/rejects and immutable provenance. Add a small licensed,
local-only source validation report; no real personal data in git or CI. Resolve #5/#6/#11 explicitly.
Reuse reviewed intake protections from #26 only after its integration is confirmed; do not treat
an open PR as part of main or inherit its CI results for this new code.
