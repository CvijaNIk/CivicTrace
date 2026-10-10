# Extension interface proposal
No dynamic plugin loader is implemented. Country connectors and independent analytical rules
are reviewed in-repository modules first. Their proposed manifest fields are:

```json
{
  "name": "example-single-bid",
  "version": "0.1.0",
  "kind": "analytical-rule",
  "maintainer": "verified GitHub identity required before release",
  "input_schema": "procurement/0.1",
  "output_schema": "evidence-passport/0.1.0",
  "data_dependencies": [],
  "methodology": "bid_count equals one; unknowns excluded",
  "example": "examples/synthetic_procurement.json",
  "limitations": ["Does not establish wrongdoing"],
  "tests": ["unknown-count", "multi-bid", "one-bid"],
  "code_license": "Apache-2.0",
  "source_license_requirements": []
}
```

Connectors must additionally specify country, publisher, access mechanism, retry/backoff,
rate/byte limits, identifiers, supported stages/versions and source-license/attribution evidence.
Their output is canonical records plus an immutable manifest and validation/quarantine report.
Rules receive canonical records and an explicit cohort/parameters/snapshot; return structured
findings with exclusions and denominators. SQL is read-only against an isolated dataset.
R exchanges files under a defined schema; never auto-execute downloaded notebooks.

Review source and dependencies; pin release artifacts and verify hashes. Never execute untrusted
extensions in privileged CI or on uploaded sensitive data. No pull_request_target execution of
contributor code, no auto-install from manifest URLs, no secrets in fork PR jobs. Future sandboxing
requires a separate threat review rather than claims of safety from a filename or manifest.
