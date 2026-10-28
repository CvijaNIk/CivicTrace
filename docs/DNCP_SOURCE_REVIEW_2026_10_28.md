# DNCP source gate review — 2026-10-28

## Decision

**Conditional go for designing the local connector in #7; no production activation or public
real-data extract in this change.** Publisher evidence now supports CC BY 4.0 reuse of the
structured procurement data. Field semantics and representative completeness remain open.
This research does not close #6 automatically. It implements a research profiler, not a connector.
Base: `69e5b496247131899fc729053d0d074ad213448f` (main). PR #26 remains a separate,
unmerged hardening proposal; its checks do not establish source rights or data quality.

## Rights evidence and interpretation

Checked official sources on 2026-10-28; response hashes, timestamps and byte lengths are in
[evidence requests](evidence/dncp-2026-10-28/requests.json). Hashes identify observations, not
trusted timestamps or archived legal opinions. Pages have no confirmed effective/version date.
Recheck at acquisition and before publication.

| Evidence | Confirmed observation | Consequence |
| --- | --- | --- |
| [DNCP catalogue](https://www.contrataciones.gov.py/datos/data) | HTTP 200; dataset HTML contains `itemprop="license"` pointing to CC BY 4.0 legalcode for tender, award and contract datasets; footer also links CC BY 4.0. Top-level metadata has a stray trailing quote. | Publisher evidence independent of the registry; do not use only the malformed top-level string as a machine-readable license. |
| [Current DNCP notice](https://www.contrataciones.gov.py/datos/aviso-legal) | HTTP 200, reached through catalogue footer. Reuse is at the user's risk; DNCP disclaims accuracy, completeness and freshness; the portal's design/code belongs to DNCP. | No conflicting structured-data redistribution prohibition was identified in this notice. This is our reading of the observed pages, not proof of third-party rights clearance. |
| [Old publisher URL](https://www.contrataciones.gov.py/datos/legal) | Web retrieval still returned 404 (also without `www` and with trailing slash). | Replace the broken reference; an unavailable old page is not evidence of a ban. |
| [OCP registry entry 63](https://data.open-contracting.org/en/publication/63) | CC BY 4.0; links the obsolete legal URL; data range Jan 2011–Aug 2026, last retrieval Aug 20, 2026, quality review Jan 2020. | Registry is an intermediary, not a replacement licensor. Its website footer license alone cannot license every underlying dataset. |

Interpretation: catalogue licensing and registry metadata are consistent for structured data;
the current legal notice supplies responsibility and access context, not an alternative explicit
license. Sufficient for a narrowly scoped local pilot with acquisition evidence. No claim that
all attachments, logos, third-party documents, personal data or website code are cleared.

[CC BY 4.0 legal code](https://creativecommons.org/licenses/by/4.0/legalcode.en), sections
2–5: reproduction, adaptation and redistribution, including commercial use, are permitted within
the licensor's rights. When sharing, retain supplied creator/copyright/license/disclaimer notices,
link the source and license, and identify changes and earlier changes. Do not imply endorsement
or impose restrictions that obstruct licensed downstream use. Database rights are addressed;
privacy, personality, trademark and patent rights are not generally granted. No accuracy warranty.
Keep external data notices separate from CivicTrace's Apache-2.0 code license.

Proposed attribution for any later approved extract (fill every placeholder):

> Source: Dirección Nacional de Contrataciones Públicas (DNCP), Paraguay, via Open Contracting
> Partnership Data Registry, publication 63. Source: [exact snapshot URL]. CC BY 4.0,
> https://creativecommons.org/licenses/by/4.0/. Retrieved [UTC]; registry snapshot [date/version].
> CivicTrace changes: [selection, compilation inherited from OCP, normalization and exclusions].
> Supplied source notices retained in [manifest]. No endorsement by DNCP or OCP.

This wording is proposed by CivicTrace, not a publisher-mandated form. Publication must separately
check personal-data necessity and local obligations; omit contacts, addresses, signatures and
natural-person identifiers from public examples. Do not fetch linked attachments automatically.

## Access verified and bounded sample

The [v3 documentation](https://contrataciones.gov.py/datos/api/v3/doc/) describes OAuth and
unauthenticated testing capped at **15 calls/minute**; older implementation guidance says four
calls/second. Use the stricter current v3 limit; production requires credentials. One exploratory
request to `/datos/api/v3/ocds/record/ocds-03ad3f-365292-1` returned 404. This proves only that
that URL/id request failed; it does not establish an API outage or successful authentication.
[Swagger](https://www.contrataciones.gov.py/datos/api/v3/doc/swagger.json) has a `/doc` basePath;
resolving the operational API route remains outside this verified JSONL path.

The registry download link resolved to version directory `4097`, annual `2025.jsonl.gz`.
One fixed Range GET downloaded **262,144 compressed bytes**, HTTP 206,
`Content-Range: bytes 0-262143/181731353`. No annual or all-time download was performed.
The prefix expanded to **2,947,318 bytes**: **22 complete lines**, plus an incomplete tail discarded.
The initial exploratory inspection viewed five lines; the reported cohort is **all 22 complete
prefix lines**, not a selection by outcome. File order is not random; results do not estimate
national or annual completeness. The 2025 partition is not a guarantee that all dates fall in 2025.

[Observed profile](evidence/dncp-2026-10-28/profile.json) records per-line SHA-256, OCID and field
states without titles, party names, contacts or individual amounts. Raw source bytes stay outside
git. The compressed prefix hash is
`3733c34d8690810a7bb72c16afb87d17f41b8299abb52530379cbff32626d9a8`.
No full snapshot hash or full gzip checksum is claimed: a truncated gzip prefix cannot verify its
trailer. A future complete local import must validate gzip EOF/CRC and hash the entire input.

| Input | Sample observation | Connector implication |
| --- | --- | --- |
| Process/release/tender identifiers | 22/22 unique valid DNCP OCIDs; 22/22 nonempty release IDs and tender IDs. Tender IDs include UUIDs; OCIDs include suffixes. | Preserve opaque strings and raw pointers; never derive tender identity by stripping OCID suffixes. |
| Reported number of tenderers | 12/22 nonnegative integers; 10 absent; no nulls. | Missing is unknown. Number of parties submitting is not automatically a count of bid submissions or lot bids. |
| Bid details | Present in 7/22 processes, 28 detail objects total; absent in 15. All 28 lack top-level bid `date` and `value`. | Neither zero bids nor complete bid coverage can be inferred. Extension/local item values require separate mapping. |
| Tender period/release dates | 22/22 timezone-bearing parseable release dates, start dates and end dates; no reversed tender periods. | Preserve publication, submission and award dates separately; some deadlines extend into 2026. Do not trust precomputed duration fields. |
| Tender amounts/currencies | 22/22 nonnegative numeric amounts and PYG codes. | Tender value is not award value, payment or expenditure. Regex checks are not a complete ISO currency validation. |
| Awards | 7/22 processes have awards, 11 objects; all 11 have ID, date, amount and PYG currency. | Preserve award multiplicity; missing awards are not proof of no award. |
| Contracts | 11 objects; 10 have IDs, amounts and PYG currencies; one lacks ID and value. All 11 lack `dateSigned`. | Quarantine incomplete child records for affected computations; never substitute award date for signing date. |
| Stage | 17 complete, three cancelled, two unsuccessful tenders. | Stage/status filters and denominator exclusions are mandatory. No findings of wrongdoing are generated. |

[OCDS reference](https://standard.open-contracting.org/latest/en/schema/reference/) defines
`numberOfTenderers` as parties submitting a bid, with detailed submissions in the
[bids extension](https://extensions.open-contracting.org/en/extensions/bids/master/).
Do not silently rename it to canonical `bid_count`. Independently validate DNCP mapping and
multi-lot/joint-bid semantics first. Registry compiled releases also do not preserve the complete
release history available from publisher record packages.

## Reproduce without a large download

From repository root on Python 3.11+:

```sh
# Explicit opt-in: exactly one fixed-host range, never an annual fallback.
python scripts/review_dncp_sample.py --fetch-prefix --save-prefix /tmp/dncp-prefix.gz.part > /tmp/dncp-live-review.json
# Offline rerun; stdout is deterministic for identical prefix bytes.
python scripts/review_dncp_sample.py --prefix /tmp/dncp-prefix.gz.part > /tmp/dncp-offline-a.json
python scripts/review_dncp_sample.py --prefix /tmp/dncp-prefix.gz.part > /tmp/dncp-offline-b.json
cmp /tmp/dncp-offline-a.json /tmp/dncp-offline-b.json
python -m unittest discover -s tests -p test_dncp_review.py -v
```

The saved prefix path must not exist. Network mode fails before reading a non-206/mismatched
response body; no paging or retries. Local input: at most 256 KiB compressed, 4 MiB expanded,
25 complete lines, 1 MiB per line and depth 32. Duplicate JSON keys/OCIDs and nonfinite constants
fail. This is a research profiler of explicitly supplied prefixes, **not** a full OCDS validator,
canonical adapter or general untrusted-file security boundary. It emits observations, not findings.
Do not commit the prefix or redirect arbitrary source records into public logs.

Network output contains retrieval time/headers; offline output does not. Compare its `records`
to the committed profile and verify the compressed prefix hash first. If version 4097 disappears
or changes, report drift; do not switch silently to another version. Hash-only evidence cannot
reconstruct missing upstream bytes. No raw personal data are required to run the synthetic tests.

Synthetic tests have explicit expectations: counts 1 and 2 are valid observations; null and absent
remain distinct; no synthetic indicator is asserted from either count. Zero amount is valid;
negative amounts, lowercase currency, invalid calendar dates and reversed periods are reported.
Duplicate keys, duplicate OCIDs, nonfinite constants, wrong shape, over-limit bytes/rows/depth and
ignored Range responses fail; partial last lines are excluded. See
[tests](../tests/test_dncp_review.py).

## Acceptance and unresolved questions

| Issue requirement | Evidence/status |
| --- | --- |
| #6 terms, attribution, bounded recipe | Publisher notice found, catalogue license corroborated; recipe and lineage above. Conditional structured-data pilot decision, no blanket redistribution clearance. |
| #6 identifiers/bids/dates/amounts completeness | Fresh 22-process probe above; wider/stage-stratified quality and source mapping still unverified. |
| #6 unknowns, rights, lineage, privacy | Separate absent/null/invalid states; hashes, source chain and public-field minimization; proposed contract below. |
| #6 reproducible synthetic example and edge cases | Five offline test methods; expected states above. No live network in tests/CI. |
| #6 current state | Updated DATA_SOURCES and CURRENT_STATE; live connector remains planned. |
| #7 local annual JSONL gzip | Proposed [input contract](DNCP_CONNECTOR_INPUT_CONTRACT.md), not implemented here. |
| #7 dependencies | #5 is open (timezone/missing/cancelled-award/duplicate-release/joint-supplier fixtures); #11 is open (canonical process/release/party/award/contract schema with decimal values, timezone dates, nullable counts; depends on #1/#5/#6). This profiler partially exercises missing/date cases but does not implement either issue. #6 remains open pending the findings below. |

Before declaring #6 fully resolved: confirm whether DNCP's reported tenderer count and local bid
items measure submissions, bidders or lots; inspect a small predeclared stratified cohort including
awarded/cancelled/unsuccessful, older/current and multi-lot cases; resolve missing contract IDs and
signing dates without imputation; verify extension schemas and registry compilation/partition rules;
record a complete, user-provided snapshot's hashes and privacy decision. No request has been sent
to DNCP or OCP. Publisher confirmation is a possible follow-up, not an invented permission.

The narrow structured-data licensing question is sufficiently supported to retain DNCP as first
candidate. No substitute source is declared cleared on the strength of a public download button.
If future artifact terms conflict or evidence disappears, hold redistribution and reassess a backup
under its own publisher terms rather than carrying DNCP's license across sources.
