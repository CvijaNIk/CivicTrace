"""Executable, synthetic-only expectations for #5; no source/network access."""

import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from civictrace.evidence import serialize_findings, single_bid_findings
from civictrace.synthetic import assess_record

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/synthetic_edge_cases.json"
CASES = json.loads(FIXTURE.read_bytes())["cases"]
TIME = "2026-10-28T09:00:00+01:00"


class SyntheticEdgeTests(unittest.TestCase):
    def test_fixture_expected_assessments_findings_schema_and_lineage(self):
        try:
            from jsonschema import Draft202012Validator, FormatChecker
        except ImportError:
            self.skipTest("jsonschema is required; CI installs dev dependencies")
        validator = Draft202012Validator(
            json.loads((ROOT / "schemas/evidence-passport.schema.json").read_text()),
            format_checker=FormatChecker(),
        )
        for case in CASES:
            with self.subTest(case=case["name"]):
                records = deepcopy(case["records"])
                before = deepcopy(records)
                raw = json.dumps(records, sort_keys=True).encode()
                kwargs = dict(snapshot_hash=sha256(raw).hexdigest(), collected_at=TIME)
                if "expected_error" in case:
                    with self.assertRaisesRegex(ValueError, case["expected_error"]):
                        single_bid_findings(records, **kwargs)
                else:
                    self.assertEqual(
                        [assess_record(r) for r in records], case["expected_assessments"]
                    )
                    findings = single_bid_findings(records, **kwargs)
                    self.assertEqual(
                        [f["source"]["original_record_id"] for f in findings],
                        case["expected_finding_record_ids"],
                    )
                    self.assertEqual(
                        serialize_findings(findings),
                        serialize_findings(single_bid_findings(records, **kwargs)),
                    )
                    for finding in findings:
                        validator.validate(finding)
                        source = finding["source"]
                        self.assertEqual(source["original_file_sha256"], kwargs["snapshot_hash"])
                        self.assertEqual(source["reference"], records[0]["source_reference"])
                        self.assertEqual(source["license"], "Apache-2.0")
                        self.assertEqual(source["collected_at"], TIME)
                        self.assertIn("Synthetic data", finding["limitations"])
                        self.assertEqual(finding["allegations"], [])
                self.assertEqual(records, before)

    def test_every_case_through_cli_no_partial_output_and_repeatable_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            for case in CASES:
                with self.subTest(case=case["name"]):
                    raw = (json.dumps(case["records"], sort_keys=True) + "\n").encode()
                    source.write_bytes(raw)
                    outputs = []
                    for run in range(2):
                        out = root / f"{case['name']}-{run}.json"
                        result = subprocess.run(
                            [
                                sys.executable,
                                "-m",
                                "civictrace.cli",
                                str(source),
                                "--collected-at",
                                TIME,
                                "--output",
                                str(out),
                            ],
                            capture_output=True,
                            text=True,
                        )
                        if "expected_error" in case:
                            self.assertNotEqual(result.returncode, 0)
                            self.assertIn(case["expected_error"], result.stderr)
                            self.assertFalse(out.exists())
                        else:
                            self.assertEqual(result.returncode, 0, result.stderr)
                            outputs.append(out.read_bytes())
                            findings = json.loads(outputs[-1])
                            self.assertEqual(
                                [f["source"]["original_record_id"] for f in findings],
                                case["expected_finding_record_ids"],
                            )
                            for finding in findings:
                                self.assertEqual(
                                    finding["source"]["original_file_sha256"],
                                    sha256(raw).hexdigest(),
                                )
                    if outputs:
                        self.assertEqual(outputs[0], outputs[1])

    def test_duplicate_order_never_selects_a_winner(self):
        for case in CASES:
            if case["name"] in {"duplicate-release", "conflicting-process", "duplicate-record"}:
                for records in [case["records"], list(reversed(case["records"]))]:
                    with self.subTest(case=case["name"], first=records[0]["record_id"]):
                        with self.assertRaisesRegex(ValueError, case["expected_error"]):
                            single_bid_findings(records, snapshot_hash="a" * 64, collected_at=TIME)

    def test_same_release_id_in_different_processes_is_not_a_duplicate(self):
        first = deepcopy(CASES[0]["records"][0])
        first.update(process_id="SYN-PROCESS-A", release_id="SYN-RELEASE-A")
        second = {**first, "record_id": "SYN-EDGE-002", "process_id": "SYN-PROCESS-B"}
        findings = single_bid_findings([first, second], snapshot_hash="a" * 64, collected_at=TIME)
        self.assertEqual(len(findings), 2)

    def test_no_inputs_and_malformed_records(self):
        self.assertEqual(single_bid_findings([], snapshot_hash="a" * 64, collected_at=TIME), [])
        for value in [None, 1, "bad", []]:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "record must"):
                single_bid_findings([value], snapshot_hash="a" * 64, collected_at=TIME)

    def test_unknown_counts_and_missing_bid_details_are_never_imputed(self):
        base = CASES[0]["records"][0]
        for field in ("bid_count", "reported_tenderer_count"):
            for state in ("absent", "null"):
                row = {**base, "bid_details": [{"id": "SYN-BID"}], field: None}
                if state == "absent":
                    del row[field]
                assessed = assess_record(row)
                self.assertEqual(assessed[field + "_state"], state)
                if field == "reported_tenderer_count":
                    self.assertIsNone(assessed[field])
                else:
                    self.assertFalse(assessed["single_bid"])
        for details in ({}, {"bid_details": None}, {"bid_details": []}):
            row = {**base, **details}
            self.assertEqual(assess_record(row)["single_bid"], True)


if __name__ == "__main__":
    unittest.main()
