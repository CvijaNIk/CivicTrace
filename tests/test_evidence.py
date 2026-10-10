import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from civictrace.evidence import serialize_findings, single_bid_findings

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/synthetic_procurement.json"
TIME = "2026-10-10T00:00:00Z"


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.raw = FIXTURE.read_bytes()
        self.records = json.loads(self.raw)
        self.kwargs = {"snapshot_hash": sha256(self.raw).hexdigest(), "collected_at": TIME}

    def test_only_one_bid_is_flagged(self):
        findings = single_bid_findings(self.records, **self.kwargs)
        self.assertEqual(
            [f["source"]["original_record_id"] for f in findings], ["SYN-001", "SYN-005"]
        )
        self.assertTrue(all(not f["allegations"] for f in findings))

    def test_reproducible_output_and_provenance(self):
        a = single_bid_findings(self.records, **self.kwargs)
        b = single_bid_findings(self.records, **self.kwargs)
        self.assertEqual(serialize_findings(a), serialize_findings(b))
        self.assertEqual(a[0]["source"]["original_file_sha256"], sha256(self.raw).hexdigest())
        changed = single_bid_findings(self.records, snapshot_hash="a" * 64, collected_at=TIME)
        self.assertNotEqual(a[0]["finding_id"], changed[0]["finding_id"])

    def test_invalid_counts_are_rejected(self):
        for value in (-1, True, "1", 1.0):
            with self.subTest(value=value):
                records = deepcopy(self.records)
                records[0]["bid_count"] = value
                with self.assertRaises(ValueError):
                    single_bid_findings(records, **self.kwargs)

    def test_invalid_identity_duplicate_and_timestamp(self):
        for field in ("record_id", "buyer_id", "supplier_id", "source_reference"):
            records = deepcopy(self.records)
            records[0][field] = ""
            with self.assertRaises(ValueError):
                single_bid_findings(records, **self.kwargs)
        with self.assertRaises(ValueError):
            single_bid_findings(self.records + [self.records[0]], **self.kwargs)
        with self.assertRaises(ValueError):
            single_bid_findings(self.records, snapshot_hash="x" * 64, collected_at=TIME)
        with self.assertRaises(ValueError):
            single_bid_findings(
                self.records, snapshot_hash="a" * 64, collected_at="2026-10-10T00:00:00"
            )

    def test_cli_export_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "findings.json"
            command = [
                sys.executable,
                "-m",
                "civictrace.cli",
                str(FIXTURE),
                "--collected-at",
                TIME,
                "--output",
                str(out),
            ]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(len(json.loads(out.read_text())), 2)
            previous = out.read_bytes()
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(previous, out.read_bytes())

    def test_schema_matches_generated_passports(self):
        try:
            from jsonschema import Draft202012Validator, FormatChecker
        except ImportError:
            self.skipTest("jsonschema is required for this check; CI installs dev dependencies")
        schema = json.loads((ROOT / "schemas/evidence-passport.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        for finding in single_bid_findings(self.records, **self.kwargs):
            validator.validate(finding)
        invalid = single_bid_findings(self.records, **self.kwargs)[0]
        invalid["source"]["original_file_sha256"] = "bad"
        self.assertTrue(list(validator.iter_errors(invalid)))


if __name__ == "__main__":
    unittest.main()
