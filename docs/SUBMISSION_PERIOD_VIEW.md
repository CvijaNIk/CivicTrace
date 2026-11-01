# Controlled synthetic submission-period view

Open `/?view=submission-period` in the existing React app, or follow **Submission periods**
from `/?view=parquet`. This is a read-only presentation of PR #43's ten controlled invented
records, not another indicator implementation and not a real-source analytics route.

## Trust and calculation boundary

[The exporter](../scripts/export_submission_view.py) calls the existing
[`submission_period.report`](../backend/src/civictrace/submission_period.py), including its
exact source-byte admission pin and shared `synthetic.tender_period` UTC calculation.
It writes the complete deterministic report and a separate compiled SHA-256 pin. `--check`
replays the original source and configuration and compares both artifacts byte for byte;
the existing Python CI matrix now requires this check. No host clock, random seed, new
benchmark, date parsing or comparison calculation is introduced.

The browser reuses the existing bounded streaming loader (64 KiB, UTF-8, timeout/abort)
and the Parquet preview's extracted shared SHA-256 gate. Only the exact reviewed report
bytes are admitted. Changed configuration/results, HTML payloads and alternate synthetic
populations fail closed. No upload, remote URL, query-controlled input, external links,
HTML execution or source adapter is exposed. React escapes source text. Source references
remain text. A pin is a byte-integrity check, not source authentication or truth.
The JSON type describes this exact compiled artifact; the hash gate is deliberately not
a general-purpose schema parser for arbitrary reports.

## Display contract

Each record separates **facts in the invented source**, **synthetic assumptions** and
**computed comparison** by semantic headings, labels, borders and backgrounds. Original
start/end strings and endpoint states remain unchanged. Invalid supplied dates stay
visible; absent and null inputs remain distinct. Exact Python decimal strings for elapsed
hours, calendar days and signed deviation are displayed without JavaScript number
coercion or rounding. Calendar days mean elapsed seconds / 86,400, not local date boundaries
or working days. Working days remain explicitly uncomputed.

The selected reference ID, hours, basis and reference description accompany each comparison.
Missing references and group values remain unknown, without fallback or zero substitution.
A valid zero duration remains zero. The fixed 24/72-hour references are invented test
parameters, neither empirical peer benchmarks nor legal minima. A below relation does
not establish an irregularity, legal violation or corruption. No Evidence Passport
finding is created or issued.

The population shows **10 total, 6 valid durations, 4 comparable, 6 excluded**; comparable
counts **below/equal/above = 3/1/0**. All six primary exclusion reasons and each record's
reason remain visible. These are record counts, not distinct procedures or risk rates.
Original pointers, source/configuration/module hashes, configuration version and source
rights/privacy metadata are shown. The complete configuration is retained in the report.

Keyboard skip navigation, native navigation/retry links and button, semantic articles and
regions, visible focus, explicit loading/error states and responsive stacked cards follow
the existing frontend. Aborted or stale loads cannot replace the current result. The
10-second timeout fails closed and permits retry.

## Reproduce

```sh
python -m pip install -e '.[dev]'
python scripts/export_submission_view.py --check
python -m pytest -q
cd frontend
npm ci
npm run build
npm test
npm run format:check
npx playwright install --with-deps chromium
npm run test:browser
npm run dev
```

Vitest adds 13 deterministic cases: independent SHA-256 check, repeatable admission,
changed/unsafe/oversized inputs, exact values and unknown/zero handling, denominators,
separation of facts/assumptions/results, HTTP integrity failure/retry, keyboard navigation,
stale-load abort, timeout and transport error. Playwright adds one full route/navigation,
known-values, keyboard/axe WCAG A/AA, 375px overflow and tampered-response/retry scenario.

Local validation on 1 November 2026: **96 Vitest tests passed**; strict TypeScript/Vite build
passed. **237 Python tests and 95 subtests passed**, zero skipped; Ruff lint/format,
documentation links, all four fixture regeneration checks, whitespace and npm audit
(zero vulnerabilities) passed. Eight local Playwright launches stopped before page assertions because Chromium
was absent; its installer failed with an invalid/truncated download. This is not passing
browser validation. Hosted CI results must be inspected independently on the published HEAD.
The existing browser gate is retained unchanged.

`analytics_enabled: false` and `synthetic: true` remain. No real DNCP analysis, automatic
finding publication, merge, deployment or production activation is included. See the
[calculation contract](SUBMISSION_PERIOD.md) for precision and comparison limitations.
