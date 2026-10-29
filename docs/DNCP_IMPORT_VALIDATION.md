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
