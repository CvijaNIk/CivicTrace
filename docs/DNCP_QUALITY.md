# DNCP stratified quality gate (research v1)

This implements an offline assessment, not production indicators. It builds on the importer in
PR #33 (`2dee16e355932421d3f3bfcd85a3e31e178bca9c`) and incorporates the research profiler,
source review and minimized historical evidence from PR #27
(`0dc03bece887ff7052b3c1dad00e8849387cae49`). Neither dependency is merged by this change.
See [the source review](DNCP_SOURCE_REVIEW_2026_10_28.md),
[local import](DNCP_LOCAL_IMPORT.md) and [actual limited check](evidence/dncp-quality-2026-10-30/README.md).
Issue #6 remains open.

## Predeclare the frame and design

Before viewing outcomes, record the exact bounded cohort, parent artifact/version/hash, terms
review, privacy/retention decision, exclusions, acquisition route, cutoff year, seed and quota.
Use a lawfully supplied local cohort, a publisher-supported bounded query/export, or the existing
fixed-range research probe. Do not download an annual database merely to fill empty cells.
Do not range-seek into arbitrary gzip offsets: these are not independent JSONL samples.
If a permitted bounded route cannot supply older/multi-lot cases, report the gap.
Never relabel a convenience/prefix frame as a population probability sample.

The target unit is one compiled procurement process (OCID), not a bid, award or contract.
Repeated OCIDs abort assessment, including repeats rejected by intake: obtain a separate,
predeclared version-resolution policy and deduplicated cohort. Never keep whichever version
happens to appear first for this assessment. Unsupported rows remain in the frame denominator
and are explicitly counted as unprofiled; they are not silently replaced.

Cross these dimensions (36 cells, including diagnostic unknowns):

| Dimension | Rule |
| --- | --- |
| Status | Exact `tender.status`: `complete`, `cancelled`, `unsuccessful`; all other/missing values are `unknown`. An active award does not replace the tender status. |
| Period | UTC year of valid `tender.tenderPeriod.startDate`: before the configured cutoff = older; at/after = recent; missing/invalid = unknown. No fallback to compilation, award or contract dates. |
| Lots | Valid distinct nonempty string IDs in `tender.lots`: one = single; more than one = multiple. Missing, null, empty or invalid IDs = unknown; absence never means one lot. |

A default exploratory quota is five per cell; CLI allows 1–25. For a broader bounded pilot,
predeclare 25 per substantive cell (12 cells = 300 processes if all exist), with cutoff 2024,
seed `dncp-quality-v1`. This is an exploratory coverage target, not a power calculation or
statistical assurance level. Keep the actual quota and all shortfalls visible. The limited
source check uses quota 25 to retain all 22 prefix rows; it does not satisfy that broader target.

Selection is bottom-k of `SHA256(seed + ':' + SHA256(ocid))` within each cell, over **all**
profileable processes in the supplied frame. It scans the entire supplied frame, including late
rows, rather than stopping when quotas fill. It is deterministic across directory/line ordering.
Use a predeclared seed without trying multiple seeds to improve outcomes. Under the pseudorandom
hash design each process in a cell of N has inclusion fraction min(k,N)/N. Both integers are
reported; an empty cell is 0/0 (undefined probability), not zero quality. No annual-population
inclusion probability is known for a prefix or an undocumented upstream cohort.

## Reproduce from a private import

From an installed checkout, first run the existing importer with its required manifest and
explicit output-byte/file budgets. Never mark `access_review=confirmed` without actual reviewed
evidence. Then:

```sh
python scripts/assess_dncp_quality.py /private/intake \
  --cutoff 2024 --per-stratum 25 --seed dncp-quality-v1 > /private/quality.json
python -m pytest tests/test_dncp_quality.py tests/test_dncp_review.py -q
```

The input must be the complete immutable, operator-controlled private importer directory.
The assessor validates the manifest contract, bounded metadata, row count, contiguous ordinals,
per-row raw hashes and the combined expanded hash in ordinal order. It profiles original `.raw`
rows before child quarantine, not the sanitized canonical contract table. Rejected structural rows
are counted as unprofiled. It does not reauthenticate an operator's manifest or independently
revalidate compressed CRC; those are importer responsibilities. Stop concurrent writers first.
The assessor writes JSON to stdout only and has no networking capability.

Importer limits remain unchanged. The research profiler has a **1 MiB** line ceiling versus the
importer's **2 MiB**, and a 25-row batch ceiling. Calling the profiler per row avoids the batch
limit; an oversized or unsupported row is explicitly unprofiled. No compatibility claim is made
for every possible accepted OCDS extension. Files above importer limits abort. Memory retains
bounded selected observations and process digests, not the entire input, but no hard RSS guarantee
is claimed. Review private reports before sharing; stdout is not automatically public-safe.

## Counts, relationships and field meaning

| Input | What is checked | Interpretation and open semantic question |
| --- | --- | --- |
| `tender.numberOfTenderers` | Absent/null/invalid/nonnegative integer, excluding booleans | Publisher-reported count. Whether it is distinct process bidders, submissions, or another scope remains unconfirmed. |
| `tender.tenderers[].id` | Entry count and distinct valid IDs | Listed participants, potentially consortium members. Repeats count once for distinct IDs. Does not prove actual submitted bids. |
| `bids.details[]` | Detail count, valid/distinct bid IDs, distinct `tenderers[].id` | A detail is not automatically a distinct bidder. The same organization can appear in several details or lots; a joint bid can contain several organizations. |
| `bids.details[].relatedLots` | Explicit references to existing lot IDs; missing vs dangling distinguished | No implicit Cartesian bid-to-lot assignment. With valid participant identities and links, report sorted per-lot distinct participant counts without publishing IDs. Otherwise the counts are unknown. |
| Tenderer comparisons | Reported vs distinct tenderer list and vs distinct bid participants: equal/different/unknown | Diagnostic only. Equality does not validate scope; a difference is not evidence of a procurement violation. |
| `date`, tender start/end, `awards[].date`, `contracts[].dateSigned` | Timezone-bearing valid instants; reversed tender periods flagged | Release/compilation date, bidding window, award date and signing date are different events. Never impute signing from an award or release date. |
| Tender, bid, award, contract `value` | Amount and currency states; zero is valid, negative/nonfinite/wrong types invalid | Values describe different scopes and are never added together. Numeric strings remain invalid for this strict research check even if an importer supports them. No exchange rates or sums are inferred. |
| `contracts[].id` | Nonempty string ID, original source field state retained | Missing identity remains missing even if the importer quarantines the contract. Process-scoped identity, not proof of a nationally unique contract. |
| Tender/award/contract status | Fixed scope-specific status enums and field states | Award and contract status cannot substitute for procedure status. Cancelled and unsuccessful procedures are separate cells, never pooled into completed procedures. |

Missing, null and malformed values remain distinct in selected observations. Empty or absent
child arrays give no applicable objects for the child coverage denominator; they are **not**
proof that no bids/contracts exist. The output keeps process-level `bid_details=null` versus
`0`, ID states, lot states and all 36 cell counts to expose these gaps. Source-specific extensions
or alternate fields require an explicit reviewed mapping, not guessing from similarly named data.
The profiler is a strict research subset, not a full OCDS validator or publisher-confirmed dictionary.

## Explicit acceptance and indicator holds

Every coverage check reports numerator, applicable denominator and result. A zero denominator
is `insufficient_data`. The engineering screening threshold is >=95% valid selected applicable
objects (integer comparison, no rounding); it is a project policy, not an OCDS requirement or
population estimate. Checks cover reported count, bid identity/participants/lot linkage, procedure
status, valid non-reversed tender dates, contract IDs/status/signing dates/money and award
status/date/money, plus bid dates/money. Pooled descriptive results are **unweighted selected-sample
coverage**, not annual rates; review observations within each stratum. Disproportionate quotas and
object counts preclude interpreting the pooled percentage as a population estimate.

Before real indicators are approved, all these additional conditions remain mandatory:

1. Exact-artifact terms/access, retention and privacy evidence reviewed for the actual cohort.
2. Population/frame definition, year/partition rules and upstream selection documented. All 12
   substantive cells meet the predeclared quota or an explicit justified nonapplicability decision;
   no unprofiled rows or unknown strata are hidden. Mere absence in this frame is not nonapplicability.
3. Publisher documentation or a reviewed source response confirms bidder/submission/consortium/lot
   scope, status semantics, extension fields and compilation rules. This PR does not fabricate it.
4. Required-field coverage passes screening and each included analytic observation has **all** its
   indicator-specific valid inputs and valid identity/linkage. The 95% screen never licenses filling
   the other 5% with zero. Exclude incomplete cases with explicit denominators/reasons.
5. Validate each proposed indicator on reviewed source cases and record exclusions. Single-bid
   analysis needs confirmed distinct bidder scope at process/lot level; timing needs the correct
   event dates; contract analysis needs identity/value and the dates relevant to its question.

The JSON deliberately returns `analytics.status=blocked` for every run in this research version.
Passing a syntax/coverage check never clears those semantic and population holds. No production
indicator is wired to this output, and no missing field creates an irregularity finding.

## Privacy and source access

Only the opt-in existing probe can access the network: one fixed 256 KiB HTTP Range, exact
206/Content-Range/final-URL checks and a 4 MiB decompression cap. Annual file size is metadata,
not bytes downloaded. The quality CLI never fetches an annual database, attachments or identities.
Raw input, party/contract IDs, names, contact details, titles, URLs and exact amounts stay private.
The minimized report contains fixed field-state enums, counts and source/row hashes; hashes are
lineage references, not a guarantee of anonymity. Historical source reviews are preserved as dated
evidence, not a new blanket legal clearance. No publisher was contacted on the user's behalf.
