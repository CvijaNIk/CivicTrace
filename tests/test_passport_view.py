"""The compiled preview reuses existing evidence, migration and replay contracts."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "passport_view", ROOT / "scripts/export_passport_view.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_repeated_example_preserves_contracts_and_unknowns():
    first = module.example()
    assert first == module.example()
    assert first["analytics_enabled"] is False
    assert first["synthetic"] is True
    legacy, migrated, *complete = first["findings"]
    assert legacy["schema_version"] == "0.1.0"
    assert {k: v for k, v in migrated.items() if k not in ("schema_version", "lineage")} == {
        k: v for k, v in legacy.items() if k != "schema_version"
    }
    assert migrated["lineage"]["status"] == "legacy-incomplete"
    assert migrated["lineage"]["environment"] is None
    assert migrated["lineage"]["decompressed_sha256"] is None
    assert len(complete) == 2
    assert all(p["lineage"]["status"] == "complete-synthetic" for p in complete)
    saved = json.loads((ROOT / "frontend/src/passport-example.json").read_text())
    for value in (first, saved):
        for p in value["findings"]:
            if p.get("lineage", {}).get("environment") is not None:
                p["lineage"]["environment"] = None
    assert first == saved
