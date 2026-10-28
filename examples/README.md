# Synthetic demonstrations
All organizations and identifiers are invented. The fixture is original project material under Apache-2.0.
It contains two single-bid records, one competitive record, one unknown count and one zero count.
Unknown and zero counts never become single-bid findings. `synthetic:` references are not public source URLs.
Run the command in the root README to create local JSON Evidence Passports. No live dataset is bundled.

`synthetic_edge_cases.json` adds 37 independent regression scenarios with exact expected
assessments, finding IDs or errors. See the [case contract](../docs/SYNTHETIC_EDGE_CASES.md)
for reproduction, optional demo fields and the remaining #11/#7 boundaries. The envelope is
for tests; only each case's `records` array is CLI input.
