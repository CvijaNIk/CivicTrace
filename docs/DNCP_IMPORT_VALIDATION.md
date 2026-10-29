# DNCP importer validation — 2026-10-29

Base: PR #29 head `677c79bf0835a5dea8e8cb1a3c5e32dc6f47ea85`.
Design: PR #27 head `415bda798e75f478cb06246a0efc0b744b922fc1`.

Local Python 3.12, installed `.[dev]`: `python -m pytest -q -rs` passed **39 tests and 88
subtests**, no skips, in 14.58 seconds. Includes all 37 existing synthetic cases and the new
DNCP intake tests. `python scripts/canonical_example.py` retained exact EUR
9007199254740993.01 joint-award total and cancelled-award exclusion.
`python -m ruff check .`, `python -m ruff format --check .`,
`python scripts/check_docs.py` and `git diff --check` passed.

All source fixtures are invented. No annual download, real-data import, public evidence output,
production enablement or actual rights determination occurred. Memory regression is tracemalloc,
not OS RSS. Manifest evidence is operator-supplied and requires review; structural checks cannot
establish legal validity. Existing hosted CI matrix targets Python 3.11–3.13; local success is not
a claim of hosted success. Check the new PR's exact head independently.

Remaining limitations and #6/#7 real-pilot gates: [operation and scope](DNCP_LOCAL_IMPORT.md).

## Atomic publication follow-up — 2026-10-29

Parent: PR #30 head `6a35dd757f69a94944c021eefb95e9138dafbdd6`. Local environment:
Linux, Python 3.12.14, pytest 9.2.0, ruff 0.17.3, jsonschema 4.26.0.
`PYTHONPATH=backend/src python -m pytest -q -rs`: **70 passed, 88 subtests passed**, no skips.
This includes 31 publication tests, full original intake checks and all synthetic edge cases.
Ruff lint/format, relative-document-link check and executable canonical example passed.
Canonical example SHA-256 remains
`7bff863869a9001715019ddf5e0ea3c906f760b9495d70749604fb292f33de40`.

Regression proof: run `test_individual_move_failure_cannot_leave_partial_output` against a separate
copy of PR #30's exact dncp.py (with its original canonical/synthetic modules). It fails at
`assert not os.path.lexists(out)`: the first canonical file remains after the second per-file move
raises injected EIO. The same test passes with the new implementation, which never uses per-file
moves. Tests for the new atomic syscall also inject final EIO/EXDEV and unsupported flags, asserting
that no final entry is created and private staging is cleaned.

The [publication contract](DNCP_PUBLICATION.md) records native-platform support, trusted-parent
assumptions, manual orphan recovery and the absence of power-loss durability guarantees.
No real DNCP data was retrieved; no public distribution or production activation occurred.
