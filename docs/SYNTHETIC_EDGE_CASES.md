# Synthetic procurement regression contract v1

Issue [#5](https://github.com/CvijaNIk/CivicTrace/issues/5) is exercised by
[37 invented cases](../examples/synthetic_edge_cases.json) and
[offline regression tests](../tests/test_synthetic_edges.py). Each case contains complete input
records and either exact assessment dictionaries plus finding record IDs, or an expected error.
The fixture envelope is a test corpus, not CLI input: the CLI accepts each case's `records` array.
All identifiers refer to invented organizations. The fixture is original Apache-2.0 test material;
its license must never be substituted for DNCP source rights. Nothing is fetched or imported.

## Executable expectations

| Cases | Expected behavior |
| --- | --- |
| Explicit `bid_count` 1 / 0 / 2 | One / no / no synthetic single-bid finding. |
| Absent/null counts | Distinct `absent`/`null` states; unknown remains null, never zero. Unknown bids exclude the demo rule. |
| One tenderer, unknown bids | No finding; reported tenderers cannot supply `bid_count`. |
| One detail, unknown bids | No finding; a detail row is not a verified submission. |
| Two tenderers, one explicit demo bid | Fields remain distinct; only explicit `bid_count` drives the demo. This is not a production interpretation of this combination. |
| Missing tenderers, four bid details without dates/values | Tenderer count remains unknown; details counted only as rows. No date/value inference. Explicit demo bid count remains independent. |
| Details absent / null / empty | Unknown / unknown / observed zero detail rows, without completeness guarantee; no fallback into either count. |
| Offsets crossing midnight | 3,600 elapsed UTC seconds. Preserve original strings. |
| Equal UTC instants / fractional seconds | Zero / 0.5 seconds; no negative-window classification. |
| Wall-clock order disagrees with UTC | Reversed period; no valid duration. |
| Missing offset, impossible date | Invalid period; no duration. |
| Missing/null endpoint | Unknown period; no duration. Only duration is unavailable; the explicit bid rule is unaffected. |
| Cancelled/unsuccessful process or award; pending award | No finding, even for `bid_count=1`; explicit exclusion reason. |
| Unknown/null status explicitly supplied | No finding; status is not silently recoded as active. |
| Complete process, active award | Eligible for the explicit demo count rule. |
| Joint suppliers without allocation | Excluded from this single-supplier demo; neither duplicate the award nor assign the full amount to each supplier. No concentration computation exists. |
| Duplicate record ID | Entire run fails; no partial CLI output. |
| Same process/release with distinct record IDs | Entire run fails; exact duplicate publication is not another observation. |
| Same process, different releases/counts | Entire run fails in either order; no latest-release guess. |
| Same release ID across different processes | Allowed; release key is process-scoped. |
| Negative, bool, string or fractional tenderer count | Error; never coerced to zero/one/null. |
| Incomplete release identity, duplicate supplier IDs, malformed details | Error with a stable message; no partial CLI output. |

The assessment API exposes exclusion reasons and field states for test review. It does not
compute population denominators, fraud probabilities, money totals, bidder eligibility, or legal
compliance. Passports retain their existing synthetic limitations, original record reference,
collection timestamp and SHA-256 of the exact CLI input bytes. Regression tests validate the
passport schema, input immutability, byte-identical reruns and failure before output creation.

## Compatibility and dependency boundaries

[DATA_MODEL.md](DATA_MODEL.md) still describes a proposed canonical schema. Optional fields here
extend only the small synthetic demo: `process_id`, `release_id`, `reported_tenderer_count`,
`bid_details`, `procurement_status`, `award_status`, `supplier_ids`, `tender_start`, `tender_end`.
Absent optional status/supplier fields retain the original demo assumptions; absence is not
proof of an active real award or sole supplier. A supplied `supplier_ids` array must be unique,
nonempty and include the legacy `supplier_id`. Two identity fields must be supplied together.
The CLI still validates legacy identities and nullable `bid_count`.

The review and proposed input contract in draft
[PR #27](https://github.com/CvijaNIk/CivicTrace/pull/27), commit
`415bda798e75f478cb06246a0efc0b744b922fc1`, inform these cases. Its 22 complete file-prefix
records are not a representative sample. Missing tenderer counts and the 28 detail rows without
basic bid dates/values motivate independent field-state cases; these tests do not reproduce or
validate real-source findings. PR #27 is separate and unmerged; no dependency on its code/files.

[#11](https://github.com/CvijaNIk/CivicTrace/issues/11) depends on #1/#5/#6 and still needs
canonical process/release/party/award/contract tables, exact decimal amounts, child linkage,
source field pointers, per-field rejects and full OCDS mapping exclusions. A reported tenderer
count must map separately from bids. These synthetic status names are not an OCDS status map.
Concentration, child-level cancellations, allocated joint awards, latest-applicable amendments,
and process/lot/award cohorts still need canonical rule tests there. These cases intentionally
reject duplicate compiled processes rather than implementing amendment reconciliation.

[#7](https://github.com/CvijaNIk/CivicTrace/issues/7) depends on #5/#6/#11. Reuse these semantic
expectations when mapping user-provided JSONL gzip. It still needs bounded decompression,
CRC/full-file hashes, strict JSON parsing, row rejects, immutable raw lineage, manifest rights,
privacy review and mapping tests. This PR does not implement or activate that connector.
No synthetic result establishes a finding about public procurement.

## Reproduce

From the repository root, install the existing development extra, then run:

```sh
python -m pip install -e '.[dev]'
python -m pytest -q
python -m pytest -q tests/test_synthetic_edges.py
ruff check .
ruff format --check .
python scripts/check_docs.py
git diff --check
```

The CLI regression executes every case twice with a fixed timestamp, checks exact expected IDs
or errors, compares successful bytes and verifies actual input-byte hashes. Temporary files
are removed automatically. No network is used by tests. CI's existing Python 3.11/3.12/3.13
matrix discovers these tests automatically; consult the draft PR for its exact-head results.
