# Canonical procurement model proposal 0.1
The current demo input is a deliberately smaller synthetic contract, not an OCDS converter.

| Field/table | Meaning and constraint |
| --- | --- |
| process.ocid | Publisher OCDS contracting-process identity; namespace retained |
| release.id/date/tag | Release identity, timezone-aware timestamp, stage; never discard amendments |
| awards/contract.id | Child IDs scoped to process and release; preserve cancellations |
| buyer/supplier.identifier | Scheme + ID + jurisdiction; never match names alone |
| money.amount/currency | Decimal value + ISO currency; missing is null, not zero |
| tender.start/end | Timezone-aware timestamps; negative intervals quarantined |
| tender.bid_count | Nonnegative integer or null; distinguish bids, bidders and valid bids |
| provenance | Snapshot hash, original record pointer, collection time, connector/schema version |

Use normalized processes, releases, parties, awards, contracts and award_suppliers tables.
A concentration view must avoid multiplying award amounts when multiple suppliers exist:
quarantine joint awards unless an allocation is explicitly documented. Choose latest applicable
release using source semantics, not filename order. Keep stable compound keys and report all
conflicting duplicates. Period, stage, category and currency define analysis cohorts.

Synthetic contract today: record_id, buyer_id, supplier_id and source_reference are nonempty
strings; bid_count is an integer >= 0 or null. Duplicate record_id fails the demo. It does not
encode award values, lots or procedures, and cannot validate real procurement records.
