"""Reproducible invented procurement example; no source records or personal data."""

from hashlib import sha256

from civictrace.canonical import award_totals, normalize, serialize

release = {
    "ocid": "SYN-PROCESS",
    "id": "notice-1",
    "date": "2026-10-28T10:00:00+01:00",
    "tender": {"status": "complete", "numberOfTenderers": 1},
    "parties": [{"id": "supplier-a"}, {"id": "supplier-b"}],
    "awards": [
        {
            "id": "award-1",
            "status": "active",
            "value": {"amount": "9007199254740993.01", "currency": "EUR"},
            "suppliers": [{"id": "supplier-a"}, {"id": "supplier-b"}],
        }
    ],
    "contracts": [
        {
            "id": "contract-1",
            "awardID": "award-1",
            "value": {"amount": "9007199254740993.01", "currency": "EUR"},
        }
    ],
}
provenance = {
    "snapshot_sha256": "a" * 64,
    "record_sha256": "b" * 64,
    "collected_at": "2026-10-28T10:00:00+01:00",
    "source_reference": "synthetic:canonical/1",
    "license": "Apache-2.0",
    "attribution": "Invented organizations only",
    "privacy_review": "Synthetic; no natural persons",
    "adapter_version": "synthetic/1",
}
model = normalize([release], provenance)
result = award_totals(model, [model["releases"][0]["id"]])
assert result["totals"] == {"EUR": "9007199254740993.01"}
print(result)
print(sha256(serialize(model).encode()).hexdigest())
release["id"] = "notice-2"
release["awards"][0]["status"] = "cancelled"
amended = normalize([release], provenance)
result = award_totals(amended, [amended["releases"][0]["id"]])
assert result["totals"] == {} and len(result["excluded_awards"]) == 1
print(result)
