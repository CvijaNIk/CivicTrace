# Synthetic submission-period comparison (#15)

Implemented only for the ten reviewed invented records in
[the fixture](../examples/synthetic_submission_period.json), protected by an exact SHA-256
pin in [the implementation](../backend/src/civictrace/submission_period.py). Arbitrary populations,
including a real record relabelled synthetic, fail closed. No DNCP connector, DuckDB query,
production indicator or activation is added by the calculation. A separate
[controlled React view](SUBMISSION_PERIOD_VIEW.md) now presents the reviewed static output. `analytics_enabled: false` remains.

## Reproduce and display

```sh
python -m pip install -e '.[dev]'
python scripts/submission_period_example.py > /tmp/submission-a.json
python scripts/submission_period_example.py > /tmp/submission-b.json
cmp /tmp/submission-a.json /tmp/submission-b.json
python -m pytest -q tests/test_submission_period.py tests/test_synthetic_edges.py
```

The JSON report displays each record's original dates, endpoint field states, period state,
UTC duration, exact selected reference/basis, signed deviation, exclusion and original pointer.
No missing duration or unmatched reference becomes zero. Equal instants are a valid zero.
`absent` (both endpoints absent), `unknown` (at least one missing/null), `invalid` and
`reversed` remain distinct period states from the shared legacy UTC calculation.
Endpoint states separately distinguish absence from explicit null; mixed missing/invalid endpoints
retain the shared missing-input precedence and original supplied values for review.
No amendment/latest-release inference, population deduplication or process aggregation is implied.

| Invented record suffix | UTC hours | Reference hours | Deviation hours | Result |
| --- | --- | --- | --- | --- |
| offset | 1 | 24 | -23 | below |
| equal | 0 | 24 | -24 | below |
| boundary | 24 | 24 | 0 | equal |
| longer | 48 | 72 | -24 | below; separate procedure group |
| missing | null | 24 | null | period_unknown |
| invalid | null | 24 | null | period_invalid |
| reversed | null | 24 | null | period_reversed |
| unmatched | 24 | null | null | benchmark_unmatched |
| absent | null | 24 | null | period_absent |
| unknown-group | 24 | null | null | group_unknown |

Denominators: **10 total records**, **6 valid durations**, **4 comparable records**,
**6 excluded from comparison**. The three below/equal/above counts use only the four comparable
records: 3/1/0. Exclusion counts reconcile to six, with exactly one primary reason per record.
Date exclusions take precedence over group/reference exclusions. There is no below-reference rate
using the full population and no division by a zero denominator. With no configured benchmarks,
the comparison denominator and all comparison counts are zero; valid durations are retained.

## Explicit reference configuration

[Configuration](../examples/synthetic_submission_benchmarks.json) contains a version and at most
100 references; file limit 64 KiB. Each has a unique ID, a complete group, positive elapsed hours
as a decimal string (up to 6 decimal places; at most 87,600 hours), a basis and a reference.
Matching requires exact equality of **procedure, category, value band and jurisdiction**. No
nearest-group fallback, observed-sample mean, universal threshold or implicit legal minimum exists.
Duplicate groups/IDs, nonfinite values, unknown units and incomplete configurations fail closed.
Only elapsed hours are accepted; working-day reference values have no supported configuration field.
The values 24 and 72 are deliberately invented test parameters, not justified real-source benchmarks.
Their explicit justification is test-case design for these invented peer groups only. Real use still
requires documented source semantics, defensible comparable cohorts and quality/rights approval.

Copy the configuration, change its version, basis and the first `elapsed_hours` to `"0.5"`, then run:

```sh
python scripts/submission_period_example.py --config /tmp/my-synthetic-benchmarks.json
```

Expected sensitivity: offset becomes above by 0.5 hours, boundary above by 23.5 hours;
the separate limited-procedure row and all raw durations remain unchanged. The report carries
the complete configuration and its exact byte hash, so changes cannot masquerade as the same run.

## Calendar time, precision and evidence

The shared `synthetic.tender_period` uses timezone-aware UTC instants. `calendar_days` means
elapsed seconds / 86,400, not local date boundaries, inclusive dates or working days. DST offsets
are honored as supplied. Working days are null with `not_computed_no_local_calendar`; no holiday
calendar, jurisdictional deadline extension or business-day assumption is invented. This is not
a legal deadline calculator. Existing Python datetime precision is microseconds; finer timestamp
fractions inherit that parser limitation. Decimal hours/days use a fixed 40-digit context for
repeatable decimal expansion. Comparison uses the unrounded supported seconds and reference;
no display rounding or date-boundary count drives classification.

The result includes original input-byte and configuration SHA-256, per-row JSON pointers and
source references, synthetic rights/privacy metadata, rule version and fingerprints of both
implementation modules. With identical code and bytes, output is identical without current time,
randomness or machine-specific metadata. The CLI has no source argument and bounds custom config
reads before parsing. Hashes establish byte identity, not source truth. Reports are diagnostic
JSON rather than Evidence Passport findings: `allegations` is empty on every record. Below a
reference is a descriptive relation and never automatically an irregularity or legal violation.

[Test coverage](../tests/test_submission_period.py) includes offsets/midnight, equal instants,
DST, microsecond boundaries, missing/null/invalid/reversed dates, independent groups, unknown
groups, missing references, changed benchmarks, invalid/ambiguous configs, deterministic CLI
reruns, decimal context independence and rejection of changed source bytes. Legacy fixture
regressions verify that extraction of the shared UTC helper preserves prior behavior.
