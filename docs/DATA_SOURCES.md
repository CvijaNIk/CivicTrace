# Public source assessment
Initial assessment 2026-10-10; DNCP reassessed 2026-10-28 using publisher pages and a bounded probe. Availability on a website
does not imply permission to redistribute. No real records are bundled, API completeness is not
validated, and no full acquisition was run in this foundation.

| Source | Access/coverage | Reuse and quality | Decision |
| --- | --- | --- | --- |
| Paraguay DNCP via OCP registry | National procurement; annual JSONL gzip, CSV and Excel | Publisher catalogue and registry identify CC BY 4.0; current legal notice found; 22-process quality probe | Conditional local-pilot candidate; field semantics and wider coverage remain open |
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

The [2026-10-28 DNCP review](DNCP_SOURCE_REVIEW_2026_10_28.md) finds a current
publisher legal notice and publisher catalogue CC BY 4.0 metadata consistent with the registry.
The obsolete `/datos/legal` link still fails; the current path is `/datos/aviso-legal`.
One 256 KiB range yielded 22 complete compiled releases. Missing tenderer counts, bid dates/values
and contract identities/signing dates prevent blanket indicator-readiness claims. No raw real
records are bundled. Retain terms/attribution evidence and apply the
[proposed connector input contract](DNCP_CONNECTOR_INPUT_CONTRACT.md). This is conditional
support for a local pilot, not completion of #6/#7 or approval of every attachment/public extract.

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
