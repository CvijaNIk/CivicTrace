"""The browser fixture is derived only from reviewed invented source bytes."""

import importlib.util
import json
from unittest.mock import patch

import pytest

spec = importlib.util.spec_from_file_location("explorer", "scripts/export_explorer.py")
explorer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(explorer)


def test_export_is_reproducible_and_preserves_unknown_zero():
    first = explorer.export()
    assert first == explorer.export() == explorer.TARGET.read_text()
    result = json.loads(first)
    assert result["analytics_enabled"] is False
    assert result["synthetic"] is True
    assert len(result["records"]) == 5
    assert result["records"][2]["bid_count"] is None
    assert result["records"][3]["bid_count"] == 0


def test_export_rejects_unreviewed_source():
    with patch("pathlib.Path.read_bytes", return_value=b"[]"):
        with pytest.raises(ValueError, match="trusted pin"):
            explorer.export()
