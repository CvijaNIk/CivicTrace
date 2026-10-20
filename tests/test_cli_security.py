import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from civictrace.evidence import single_bid_findings
from civictrace.ingestion import MAX_INPUT_BYTES, MAX_RECORDS


class CliSecurityTests(unittest.TestCase):
    def assert_rejected(self, raw):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.json"
            output = Path(directory) / "output.json"
            source.write_bytes(raw)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "civictrace.cli",
                    str(source),
                    "--output",
                    str(output),
                    "--collected-at",
                    "2026-10-10T00:00:00Z",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse(output.exists())

    def test_duplicate_count_is_not_silently_reinterpreted(self):
        self.assert_rejected(
            b'[{"record_id":"x","buyer_id":"b","supplier_id":"s",'
            b'"source_reference":"synthetic","bid_count":2,"bid_count":1}]'
        )

    def test_oversized_input_has_no_output(self):
        self.assert_rejected(b"[]" + b" " * MAX_INPUT_BYTES)

    def test_invalid_rows_and_encoding_have_controlled_errors(self):
        for raw in (b"[null]", b"[1]", b"[[]]", b"[", b"\xff"):
            with self.subTest(raw=raw):
                self.assert_rejected(raw)

    def test_record_and_identity_limits_apply_to_direct_callers(self):
        kwargs = {"snapshot_hash": "a" * 64, "collected_at": "2026-10-10T00:00:00Z"}
        record = {
            "record_id": "x",
            "buyer_id": "b",
            "supplier_id": "s",
            "source_reference": "synthetic",
            "bid_count": 1,
        }
        for rows in (
            [None],
            [record] * (MAX_RECORDS + 1),
            iter([record]),
            [{**record, "source_reference": "a" * 4097}],
        ):
            with self.assertRaises(ValueError):
                single_bid_findings(rows, **kwargs)

    def test_record_limit_in_decoder(self):
        self.assert_rejected(json.dumps([{}] * (MAX_RECORDS + 1)).encode())

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO is a POSIX-only input type")
    def test_fifo_is_rejected_without_waiting_for_a_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.fifo"
            os.mkfifo(source)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "civictrace.cli",
                    str(source),
                    "--output",
                    str(Path(directory) / "output.json"),
                    "--collected-at",
                    "2026-10-10T00:00:00Z",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("regular file", result.stderr)
