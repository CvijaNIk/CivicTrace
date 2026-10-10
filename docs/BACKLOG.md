# v0.1 actionable backlog

These 20 real issues extend the foundation rather than repeat already implemented scaffolding.
Native milestones could not be created: the available GitHub connector has no milestone-creation
operation. Proposed milestone is recorded in every issue and in ROADMAP.md.

| Issue | Task | Priority | Difficulty | Dependencies |
| --- | --- | --- | --- | --- |
| [#1](https://github.com/CvijaNIk/CivicTrace/issues/1) | Extend architecture decisions with measured workload budgets | P1 | medium | None |
| [#2](https://github.com/CvijaNIk/CivicTrace/issues/2) | Lock and verify Python release environments | P1 | medium | #1 |
| [#3](https://github.com/CvijaNIk/CivicTrace/issues/3) | Initialize accessible React TypeScript Vite frontend | P1 | medium | #1 |
| [#4](https://github.com/CvijaNIk/CivicTrace/issues/4) | Extend CI with frontend and dependency integrity gates | P1 | medium | #2, #3 |
| [#5](https://github.com/CvijaNIk/CivicTrace/issues/5) | Add deterministic synthetic procurement edge cases | P1 | easy | None |
| [#6](https://github.com/CvijaNIk/CivicTrace/issues/6) | Verify DNCP source rights and required indicator fields | P0 | medium | None |
| [#7](https://github.com/CvijaNIk/CivicTrace/issues/7) | Implement bounded local DNCP OCDS import connector | P0 | hard | #5, #6, #11 |
| [#8](https://github.com/CvijaNIk/CivicTrace/issues/8) | Add canonical validation and data quality reporting | P0 | medium | #5, #11 |
| [#9](https://github.com/CvijaNIk/CivicTrace/issues/9) | Implement version-aware deduplication and identity rules | P0 | hard | #7, #8 |
| [#10](https://github.com/CvijaNIk/CivicTrace/issues/10) | Implement versioned Parquet snapshots and manifests | P0 | medium | #7, #8, #9 |
| [#11](https://github.com/CvijaNIk/CivicTrace/issues/11) | Implement canonical procurement schema and OCDS mapping | P0 | hard | #1, #5, #6 |
| [#12](https://github.com/CvijaNIk/CivicTrace/issues/12) | Create isolated DuckDB analytical query layer | P0 | medium | #10, #11 |
| [#13](https://github.com/CvijaNIk/CivicTrace/issues/13) | Implement supplier concentration with transparent denominators | P1 | medium | #9, #12, #16, #17 |
| [#14](https://github.com/CvijaNIk/CivicTrace/issues/14) | Implement production single-bid procurement indicator | P1 | medium | #8, #12, #16, #17 |
| [#15](https://github.com/CvijaNIk/CivicTrace/issues/15) | Implement submission-period indicator with contextual benchmarks | P1 | medium | #8, #12, #16, #17 |
| [#16](https://github.com/CvijaNIk/CivicTrace/issues/16) | Implement source provenance and snapshot lineage | P0 | medium | #6, #7, #10 |
| [#17](https://github.com/CvijaNIk/CivicTrace/issues/17) | Extend Evidence Passport beyond the synthetic demo | P1 | medium | #11, #16 |
| [#18](https://github.com/CvijaNIk/CivicTrace/issues/18) | Build initial public procurement records interface | P1 | medium | #3, #10, #17 |
| [#19](https://github.com/CvijaNIk/CivicTrace/issues/19) | Add buyer supplier and contract search and filters | P1 | medium | #18 |
| [#20](https://github.com/CvijaNIk/CivicTrace/issues/20) | Implement reproducible exports and end-to-end release validation | P1 | hard | #4, #13, #14, #15, #19 |

Start with #6 (source rights and fields) and #5 (synthetic edge cases); #11 precedes #7.
First-contribution scopes: #1 documented workload budget recipe, #5 synthetic fixtures and
#6 collection of official source references. Source-rights conclusions require maintainer review.
The critical path is #6 → #11/#7 → #8/#9/#10 → #12/#16/#17 → #13/#14/#15 → #18/#19/#20.
Frontend setup #3 and CI #4 can proceed alongside the source work.
