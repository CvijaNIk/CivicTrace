# Bounded local input remediation

Base: `69e5b496247131899fc729053d0d074ad213448f`, default branch `main`.
No active PR overlapped this source at the start of the increment.

The original CLI called `Path.read_bytes()` and `json.loads()` without byte,
nesting or row budgets. JSON duplicate keys silently replaced previous values,
including `bid_count`; a named pipe could block indefinitely. Invalid JSON,
encoding and non-object rows could produce uncontrolled tracebacks.
Severity: Medium local resource/input-integrity hardening. No public remote
endpoint, production exploit or compromise is demonstrated.

The new intake checks the opened descriptor, limits reads even if file size
changes, scans depth before JSON object creation and decodes strict UTF-8.
It rejects duplicate keys, nonfinite numbers and oversized numeric tokens.
Record/identity limits also apply to direct evidence-library callers.
All accepted original input bytes feed the unchanged snapshot hash; the
synthetic finding IDs and canonical output semantics remain unchanged.

## Actual verification

- Final Python 3.12 suite: **24 passed, zero skipped**, including existing
  JSON Schema validation and deterministic provenance/output tests.
- 18 new security tests include byte/depth/numeric/row limits, invalid shapes,
  duplicate counts, UTF-16/32 depth-bypass attempts, nonfinite constants and
  exponents, exact byte boundary, escaped delimiters and POSIX FIFO rejection.
- The six CLI/library regression methods were run separately against the
  original CLI/evidence code. They failed with 7 assertion failures and 2
  errors (subtests included), including duplicate/oversized input acceptance
  and a five-second FIFO timeout. This was a safe local synthetic exercise.
- Ruff 0.11.13 lint/format checks and `scripts/check_docs.py` passed.
- Test tools installed in an isolated directory: pytest 8.3.5 and jsonschema
  4.23.0. No project dependency manifest or workflow changed. Existing broad
  development dependency ranges still require a reviewed lock/provenance pass.

Reproduce with existing development dependencies:
`PYTHONPATH=backend/src python -m pytest -q`, `ruff check .`,
`ruff format --check .`, `python scripts/check_docs.py`.
No hosted CI pass, full fuzzing, OS resource sandbox, external-source intake
or deployed protection is claimed. Exact-head CI is recorded in the draft PR.

## Compatibility and remaining work

Larger inputs, deeply nested JSON, duplicate keys, nonfinite numbers, other
encodings and overlong identifiers are deliberately rejected. The synthetic
demo remains compatible. Do not raise limits or add a bypass flag without
resource tests and a reviewed input contract. The loader is bounded, not
streaming; parsing and output still require memory within these budgets.

Restore/retention and cryptographic source authenticity are separate concerns.
Dependency/SAST/secret history scanning, parser fuzzing and real runtime
resource enforcement remain outstanding. No migration or customer data change.
Rollback is a reviewed revert of this increment; it restores the unsafe input
path. Nothing was merged or deployed.
