# Limited DNCP source compatibility check — 2026-10-30

`report.json` is the minimized result of one bounded research-prefix recheck and the new offline
quality assessor. This is not a representative pilot or a full annual data validation.

## Acquisition and reproducibility

- Existing opt-in command: `python scripts/review_dncp_sample.py --fetch-prefix --save-prefix
  /private/prefix.gz`; stdout retained privately as acquisition/profile metadata.
- Exactly 262,144 compressed bytes fetched from the fixed version-4097 annual 2025 artifact,
  HTTP 206. Exact URL, retrieval timestamp, ETag, Content-Range and prefix hash are in the report.
- Prefix hash `3733c34d8690810a7bb72c16afb87d17f41b8299abb52530379cbff32626d9a8`
  matches the historical profile. This recheck supplies no additional records or sampling breadth.
- `decode_prefix` yields 22 complete lines and discards 1,083,944 partial-line bytes. It does not
  validate the annual gzip CRC or claim a complete annual-file hash.
- Repack only complete lines: `expanded = b'\n'.join(lines) + b'\n'`;
  `gzip.compress(expanded, mtime=0)`. The local repack is 212,614 compressed / 1,863,374 expanded
  bytes. Its hashes are in `design`; these identify the **derived cohort**, not the annual source.
- Import the repack under `dncp-local/1`, pinning adapter
  `2dee16e355932421d3f3bfcd85a3e31e178bca9c`. Manifest selection records the parent prefix hash,
  exact extraction recipe, partial-line exclusion and convenience frame. Access attestation is
  limited to the existing authorized fixed-range local research recipe and the same artifact's
  structured-data terms in the [dated review](../../DNCP_SOURCE_REVIEW_2026_10_28.md), including
  its 2026-10-30 recheck. No new legal clearance, annual license refresh or permission to publish
  source records is asserted. Private mode-0700 directory; no raw files uploaded or committed.
- Explicit import budget: 33,554,432 logical bytes / 100 files. Full CRC/hash verification applies
  to the locally repacked gzip only. All 22 rows accepted; one original contract is quarantined
  by the importer and remains visible as missing-ID/value in the raw quality observations.
- Assess with cutoff 2024, quota 25, seed `dncp-quality-v1`. All 22 remain selected, because
  every populated stratum contains fewer than 25. The assessor's full report excluding
  `source_check` is byte-reproducible (sorted, indented JSON) from that immutable intake.
  `source_check` adds the captured acquisition metadata, actual importer summary and attribution.
- No raw source data is bundled. Reacquisition only reproduces this check if the fixed artifact
  still yields the same hash; stop and review changes if it differs. Synthetic tests reproduce
  sampler behavior completely offline without requiring any source access.

## Observed results (this prefix only)

| Scope | Observation |
| --- | --- |
| Status | 17 complete; 3 cancelled; 2 unsuccessful |
| Period | All recent by UTC tender start year, cutoff 2024; **zero older cases** |
| Lots | Complete: 10 single / 7 multiple; cancelled: 3 single; unsuccessful: 2 single |
| Coverage | Only 4 of 36 cells populated; all 4 below quota 25; 32 empty including diagnostic unknown cells |
| Reported tenderers | Valid in 12/22 processes |
| Bid details | 28 details across 7 processes; all 7 have valid distinct bid IDs and participant IDs |
| Bid event/value | 0/28 top-level bid dates and 0/28 bid money fields valid |
| Multi-lot linkage | 0/7 multi-lot processes have usable explicit bid-to-lot links; per-lot participation remains unknown |
| Contracts | 10/11 IDs and money valid; 0/11 signing dates; one missing ID/value/status |
| Awards | 11/11 award date/status/money syntactically valid |

These are descriptive observations of a convenience prefix, not missingness estimates for DNCP,
not confirmation that source events do not exist, and not evidence of misconduct. Profiled values
can be syntactically valid while semantically unsuitable for an indicator. No amount, date, name,
contact field or source contract/party ID is published in this new report.

## Still required

A lawfully obtained, bounded cohort spanning older/recent periods and cancelled/unsuccessful
multi-lot procedures; reviewed population and compilation rules; confirmed bidder/consortium/
submission/lot semantics; alternate bid event/value and contract-signing mappings if documented;
reviewed indicator-specific exclusions. Issue #6 remains open and `analytics.status` is blocked.

Attribution: Dirección Nacional de Contrataciones Públicas (DNCP), Paraguay, via Open Contracting
Partnership publication 63, version 4097, annual 2025 artifact, retrieved 2026-10-30.
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), under the narrowly reviewed structured-data
scope. Transformations: OCP compilation inherited; prefix selection, local complete-line repack,
field-state minimization and stratified profiling. No endorsement by DNCP or OCP. Raw publication
and attachments are excluded. See [quality method](../../DNCP_QUALITY.md).

## Local validation

Python 3.12.14: 111 tests passed, 95 subtests passed. Ruff 0.17.3 lint and format checks,
relative-document links and whitespace checks passed. The actual CLI output matches the
committed assessment after excluding the captured `source_check` wrapper. Tests cover all 12
substantive synthetic cells, input-order invariance, seed sensitivity, quota/threshold boundaries,
empty/shortfall/unknown strata, duplicate process rejection, identity and lot-link diagnostics,
missing/null/empty distinctions, raw/expanded hash failures, importer child-quarantine visibility,
and the 1 MiB profiler versus 2 MiB importer boundary. Hosted CI is a separate check on the
exact PR head; local results do not establish other Python versions or production readiness.
