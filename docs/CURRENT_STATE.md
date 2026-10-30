# Current state
Foundation merged through PR #21 on 2026-10-10; not a v0.1 product release.
Existing main contained README, Apache-2.0 LICENSE and Python .gitignore; license and ignore file
are preserved. No unrelated project code or private materials were imported.

Implemented: original synthetic procurement fixture; offline Python CLI; deterministic single-bid
Evidence Passport JSON output; strict demo count/identity checks; JSON Schema; meaningful smoke,
provenance and CLI tests; documentation, governance, source assessment, CI and templates.

Planned: all live connectors, canonical real-source validation, three production indicators,
DuckDB/Parquet processing, React explorer, search, CSV exports, graph/R/cyber modules and hosting.
No donation account or FUNDING.yml. Branding remains provisional with known conflicts.
DNCP has a [source review](DNCP_SOURCE_REVIEW_2026_10_28.md) rechecked against live publisher
pages on 2026-10-30. CC BY 4.0 reuse is documented narrowly for the identified structured datasets
and OCP publication 63 artifact, subject to attribution and privacy/third-party exclusions. A
256 KiB range probe profiled 22 complete processes; field semantics and wider completeness remain
open. No new real data was downloaded for the recheck.
A bounded research profiler and synthetic tests are implemented; the
[connector input contract](DNCP_CONNECTOR_INPUT_CONTRACT.md) is a proposal. No real connector,
automatic intake, production activation or public source-data extract is implemented. Exact-artifact
terms capture, privacy review and representative field-quality work remain gates. PR #26 is still
separate/unmerged.

The docs/product-roadmap branch expands the README into a proposed long-term product blueprint:
six detailed modules, public/local/research workflows, shared capabilities, dependencies, v0.6
Studio integration and v0.7 hardening milestones, and a v1.0 completion checklist. ROADMAP.md
is aligned with that direction. These documentation changes implement no additional application
features; later-stage capabilities remain planned and exploratory features are separated.

Verification and GitHub issue links are recorded in VALIDATION.md and BACKLOG.md. Next task:
representative DNCP field/semantic validation and a bounded, local connector with synthetic mapping
tests; retain the explicit local-only/privacy gate for any real-data pilot.
