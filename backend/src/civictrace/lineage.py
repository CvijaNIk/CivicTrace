"""Local synthetic provenance. Byte integrity is not source authentication or truth."""

import json
import platform
from copy import deepcopy
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .evidence import explorer_record, single_bid_findings, validate_record, validate_timestamp

DISCLAIMER = (
    "Hashes establish byte identity only, not source truth, authentic acquisition time, "
    "publisher identity, legal admissibility or permission to redistribute."
)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def digest(raw):
    return sha256(raw).hexdigest()


def environment():
    packages = {}
    for name in ("civictrace", "pyarrow", "duckdb"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = "not-installed"
    return dict(
        python=platform.python_version(),
        implementation=platform.python_implementation(),
        platform=platform.platform(),
        packages=packages,
    )


def implementation(name):
    return digest(Path(__file__).with_name(name + ".py").read_bytes())


def artifact(name, raw, media):
    return dict(id=name, sha256=digest(raw), media_type=media)


def step(operation, version, inputs, output, module):
    return dict(
        operation=operation,
        version=version,
        inputs=inputs,
        output=output,
        implementation_sha256=implementation(module),
    )


def migrate_passport(passport):
    """Lossless 0.1 -> 0.2; never manufacture historical hashes/environment/rights."""
    result = deepcopy(passport)
    if result.get("schema_version") == "0.2.0":
        return result
    if result.get("schema_version") != "0.1.0":
        raise ValueError("unsupported passport version")
    source = result["source"]
    result["schema_version"] = "0.2.0"
    result["lineage"] = dict(
        contract="civictrace-lineage/1",
        status="legacy-incomplete",
        synthetic_only=True,
        analytics_enabled=False,
        original_file_sha256=source["original_file_sha256"],
        decompressed_sha256=None,
        original_pointer=None,
        source_date=None,
        collection_time=source["collected_at"],
        rights=dict(
            license=source["license"],
            evidence=None,
            attribution=None,
            redistribution="unknown; retain existing restrictions",
            privacy_review=None,
            registry_transformation=None,
        ),
        artifacts=[],
        transformations=[],
        environment=None,
        limitations=[DISCLAIMER, "Legacy migration: missing provenance remains unknown."],
    )
    return result


def fixture_passports(raw, *, expected_sha256, collected_at):
    """All five explorer results and the two existing synthetic findings, pinned to source bytes.

    The reviewed fixture is uncompressed: decompressed bytes equal original bytes.
    Collection time is caller asserted; source publication time is unknown.
    """
    validate_timestamp(collected_at)
    pin = "bb30164c2944433984b29855a5416be52e640fd94a48916ef9327ed9697bcef2"
    if expected_sha256 != pin or digest(raw) != pin:
        raise ValueError("reviewed synthetic fixture pin mismatch")
    records = json.loads(raw)
    findings = single_bid_findings(records, snapshot_hash=pin, collected_at=collected_at)
    passports = []
    for index, record in enumerate(records):
        validate_record(record)
        row_bytes = encoded(record)
        common = dict(
            contract="civictrace-lineage/1",
            status="complete-synthetic",
            synthetic_only=True,
            analytics_enabled=False,
            original_file_sha256=pin,
            decompressed_sha256=pin,
            original_pointer=f"/{index}",
            source_date=None,
            collection_time=collected_at,
            rights=dict(
                license="Apache-2.0",
                evidence="LICENSE",
                attribution="CivicTrace contributors; invented organizations only",
                redistribution="synthetic example only",
                privacy_review="Invented fixture; no natural persons or client data",
                registry_transformation="not applicable; no registry enrichment",
            ),
            artifacts=[
                artifact("original", raw, "application/json"),
                artifact("record", row_bytes, "application/json"),
            ],
            transformations=[
                step("JSON array pointer selection", "1", ["original"], "record", "lineage")
            ],
            environment=environment(),
            limitations=[DISCLAIMER, "Synthetic data; source date unknown"],
        )
        # Reuse the actual frontend export projection, including unknown/zero states.
        projection = explorer_record(record)
        explorer_lineage = deepcopy(common)
        explorer_lineage["artifacts"].append(
            artifact("explorer", encoded(projection), "application/json")
        )
        explorer_lineage["transformations"].append(
            step("explorer projection", "civictrace-explorer/1", ["record"], "explorer", "evidence")
        )
        passports.append(
            dict(
                result_id=record["record_id"],
                result_kind="explorer-record",
                result=projection,
                lineage=explorer_lineage,
            )
        )
        for finding in findings:
            if finding["source"]["original_record_id"] != record["record_id"]:
                continue
            passport = deepcopy(finding)
            passport["schema_version"] = "0.2.0"
            common = deepcopy(common)
            common["artifacts"].append(artifact("finding", encoded(finding), "application/json"))
            common["transformations"].append(
                step("single-bid", "0.0.1", ["record"], "finding", "evidence")
            )
            passport["lineage"] = common
            passports.append(
                dict(
                    result_id=finding["finding_id"],
                    result_kind="finding",
                    result=passport,
                    lineage=deepcopy(common),
                )
            )
    return passports


def verify_fixture_passports(passports, raw, *, expected_sha256, collected_at):
    """Replay computations, code fingerprints, metadata and pointers; fail on any change.

    Verify in the recorded environment. A changed environment deliberately requires review.
    The independently supplied fixture pin prevents self-consistent evidence replacement.
    """
    expected = fixture_passports(raw, expected_sha256=expected_sha256, collected_at=collected_at)
    if passports != expected:
        raise ValueError("synthetic provenance replay mismatch")
    return dict(
        results=5,
        findings=2,
        integrity_verified=True,
        source_truth_verified=False,
        acquisition_time_authenticated=False,
        analytics_enabled=False,
    )


def snapshot_record_lineage(directory, *, expected_snapshot_id):
    """Resolve every original row of a verified synthetic snapshot, without running analytics.

    Inventory verification alone does not establish correct transformations. Replay the
    importer and writer into a private temporary directory and compare complete manifests.
    This is deliberately local and bounded by the snapshot's recorded import/write budgets.
    """
    import tempfile

    from .dncp import OutputBudget
    from .snapshots import build_snapshot, read_json, verify_snapshot

    directory = Path(directory)
    manifest = verify_snapshot(directory)
    if manifest["snapshot_id"] != expected_snapshot_id:
        raise ValueError("snapshot pin mismatch")
    source = manifest["source"]
    if any(
        source.get(k) not in {"synthetic-only", "synthetic-example"}
        for k in ("source_url", "resolved_url", "selection", "privacy_review")
    ):
        raise ValueError("synthetic only")
    # Replay uses precisely the importer configuration, not current defaults.
    with tempfile.TemporaryDirectory(prefix="civictrace-lineage-") as tmp:
        tmp = Path(tmp)
        replay = build_snapshot(
            directory / "evidence", tmp / "snapshot", budget=OutputBudget(**manifest["limits"])
        )
        if replay != manifest:
            raise ValueError("snapshot transformation replay mismatch")
    rows = []
    for path in sorted((directory / "evidence").glob("*.canonical.json")):
        model = read_json(path)
        release = model["releases"][0]
        rows.append(
            dict(
                canonical_file=path.name,
                original_record_id=release["source_record"]["ocid"],
                release_source_id=release["source_id"],
                raw_file=model["intake"]["raw_file"],
                canonical_sha256=digest(path.read_bytes()),
                entities={
                    table: [
                        dict(
                            identity={
                                k: row[k]
                                for k in ("id", "award_id", "party_id", "release_id", "process_id")
                                if k in row
                            },
                            pointer=row.get("pointer", ""),
                        )
                        for row in model[table]
                    ]
                    for table in (
                        "processes",
                        "releases",
                        "parties",
                        "awards",
                        "contracts",
                        "award_suppliers",
                    )
                },
                provenance=release["provenance"],
                original_pointer="",
                source_date=release.get("date"),
            )
        )
    return dict(
        contract="civictrace-snapshot-lineage/1",
        snapshot_id=expected_snapshot_id,
        original_file_sha256=source["compressed_sha256"],
        decompressed_sha256=source["expanded_sha256"],
        source=source,
        rows=rows,
        artifacts=manifest["files"],
        writer=manifest["writer"],
        collection_time=source["retrieved_at"],
        environment_scope="verification environment; historical full environment unknown",
        transformations=[
            dict(operation=name, implementation_sha256=implementation(name))
            for name in ("dncp", "canonical", "snapshots")
        ],
        environment=environment(),
        analytics_enabled=False,
        limitations=[DISCLAIMER],
    )


def cohort_result_passport(directory, result, *, expected_snapshot_id):
    """Bind an existing cohort diagnostic to its complete input population by replay.

    Membership is the entire input population (included and excluded), never a claim
    that every source row contributed to the exact sum. The fixed cohort is preserved.
    """
    from .analytics import Cohort, QueryBudget, query_snapshot

    replay = query_snapshot(
        directory,
        expected_snapshot_id=expected_snapshot_id,
        cohort=Cohort(**result["cohort"]),
        budget=QueryBudget(**result["resources"]["budget"]),
    )
    if result != replay:
        raise ValueError("cohort result replay mismatch")
    lineage = snapshot_record_lineage(directory, expected_snapshot_id=expected_snapshot_id)
    lineage["transformations"].append(
        dict(
            operation="cohort_summary",
            version=result["query_version"],
            implementation_sha256=implementation("analytics"),
            parameters=result["cohort"],
            output_sha256=digest(encoded(result)),
        )
    )
    return dict(
        schema_version="civictrace-cohort-passport/1",
        result=deepcopy(result),
        lineage=lineage,
        input_scope="all imported source rows, including excluded rows; not only contributors",
    )
