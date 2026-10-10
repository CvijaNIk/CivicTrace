# Public source assessment
Assessed 2026-10-10 using official documentation and the OCP registry. Availability on a website
does not imply permission to redistribute. No real records are bundled, API completeness is not
validated, and no full acquisition was run in this foundation.

| Source | Access/coverage | Reuse and quality | Decision |
| --- | --- | --- | --- |
| Paraguay DNCP via OCP registry | National procurement; annual JSONL gzip, CSV and Excel | Registry lists CC BY 4.0; OCDS lots/bids/local extensions; older quality review | Recommended first bounded historical dataset, with publisher-terms gate |
| EU TED | Official search API and bulk notice downloads; Europe | Strong reach; eForms/legacy formats and notice stages require mapping; check specific terms | Later connector; greater normalization cost |
| OCP Data Registry | Multi-country compiled OCDS releases and downloads | Registry is an access layer, not one universal dataset license; source-specific quality | Use publisher-specific manifest and preserve processing lineage |
| GLEIF | Global LEI records and relationships | Official open-data page declares CC0; LEI coverage is not all companies | v0.3 enrichment, not procurement launch dataset |
| OFAC | Official SDN and consolidated list download service | Preserve effective date, list/program and original identity details; confirm reuse/privacy scope | Later authorized screening, not procurement launch |
| Serbia procurement portal | National public portal | Stable bulk API/export, license and required indicator fields not established here | Valuable follow-on; do not build on unverified scraping assumptions |
| UK Contracts Finder | Official OCDS API and CSV described by GOV.UK | English-language alternative; coverage/transition and source license must be checked | Backup candidate after field and freshness assessment |

## Recommended first dataset
Use one historical annual DNCP snapshot, then generate a deliberately bounded extract, selected
by explicit process/period criteria. Start with the registry JSONL export to avoid an API key
assumption. Retain the entire snapshot hash even if importing a subset; record exact row selection,
compression/decompression hashes and registry retrieval date separately from CivicTrace collection.
Do not download or serve the all-time dataset by default.

The registry lists CC BY 4.0 with attribution, license link and change disclosure requirements.
Its linked publisher legal page returned 404 during this assessment. Therefore recommendation
is provisional for distribution: resolve publisher terms and retain license evidence before
publishing any derived extract. Acquisition rights, personal-data minimization, field coverage,
compression expansion and performance must all pass review. The registry's quality review date
is old; run fresh completeness checks for bids, tender dates, awards, currencies and identifiers.
Missing inputs make individual indicators unavailable; never infer a zero or impute one bid.

## Verified documentation links
- [DNCP registry entry and data quality](https://data.open-contracting.org/en/publication/63)
- [OCDS](https://standard.open-contracting.org/latest/en/)
- [TED developer docs](https://docs.ted.europa.eu/api/latest/index.html)
- [TED data reuse](https://ted.europa.eu/en/help/data-reuse)
- [GLEIF open data](https://www.gleif.org/en/about/open-data)
- [OFAC Sanctions List Service](https://ofac.treasury.gov/sanctions-list-service)
- [Serbian procurement portal](https://jnportal.ujn.gov.rs/)
- [Contracts Finder API](https://www.contractsfinder.service.gov.uk/apidocumentation/home)

These are reference links, not statements that a production connector has been verified.
