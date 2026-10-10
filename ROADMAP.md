# Proposed roadmap
No dates are promised. Foundation 0.0.1 contains documentation and a synthetic Python demo only.

| Milestone | Scope | Dependencies / release gate |
| --- | --- | --- |
| v0.1 Public Procurement Explorer | One verified source, normalization, three meaningful indicators, searchable records, Evidence Passports, CSV/JSON exports | Rights and field assessment → connector/schema/identity → snapshots/SQL/provenance → rules → UI/filters → exports and E2E |
| v0.2 Local Financial Forensics | Local CSV/Parquet, journal/payment tests, reusable SQL, reports; Excel after parser review | v0.1 contracts; size caps, formula-safe exports and verified no-upload behavior |
| v0.3 Corporate Networks | Public identifiers, sourced relationships, temporal graph, enrichment | Evidence lineage; exact identity/candidate distinction and GLEIF source checks |
| v0.4 Statistical Research | Python/R, peer benchmarks, econometrics, notebooks | Reproducible snapshots; model assumptions, diagnostics and validation |
| v0.5 Passive Cyber Intelligence | Public advisories, vulnerability datasets, infrastructure evidence, integrity | Reviewed source rights/privacy; no unauthorized scanning |
| v0.6 Investigation Studio Integration | Local cases, review states, timelines, cross-module findings and portable packages | Passport compatibility; source rights; correction lineage; save/open/delete and safe exports |
| v0.7 Release Candidate and Hardening | Accessibility, migration/recovery, performance, dependency locks and complete workflows | Published measured limits; security review; supported-platform installation and reproducibility |
| v1.0 Integrated Investigation Platform | Unified public research + local private analysis, packages, mature extension contracts | Prior gates, measured performance, comprehensive security/accessibility/reproducibility review |

## v0.1 gate
Choose source only after checking fields and licensing; if a proposed indicator lacks reliable input,
report that gap and select another documented source/indicator. Never substitute fabricated live
records. Two demo passport results do not meet the v0.1 release gate. Public hosting must contain
only licensed, minimized records; lock dependencies and measure browser/file limits before release.

See [20-task backlog](docs/BACKLOG.md). The next implementation task is the bounded source-field
and rights assessment followed by the DNCP import connector. Naming clearance is a launch gate.

## Integration and v1.0 readiness
The [README product roadmap](README.md#roadmap-to-v10) describes the six modules, target user
workflows, shared capabilities and dependency sequence. Investigation Studio grows through earlier
milestones; v0.6 integrates existing evidence handling rather than postponing it until that release.
v0.6 and v0.7 are proposed bridge milestones added to make the path to a usable v1.0 explicit.
The current 20 issues cover v0.1, not a fully scheduled multi-year implementation plan.

The [v1.0 checklist](README.md#what-makes-v10-ready) requires usable public exploration, local
financial analysis, sourced corporate graphs, reproducible Python/R and passive cyber workflows,
integrated local cases, reviewable Passports, reproducible reference cases, accessibility,
tested migrations/recovery/deletion, measured performance, security review and sustainable ownership.
Public access and local analysis remain free without mandatory registration.

After v1.0, additional countries, licensed trade/ownership sources, translations, opt-in local
refresh, organizational self-hosting, larger-workload processing and evaluated source-grounded AI
remain exploratory directions. They require separate scope, evidence of demand and review.
