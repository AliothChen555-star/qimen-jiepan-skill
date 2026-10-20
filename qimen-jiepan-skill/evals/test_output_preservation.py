"""CLI writes must not destroy the frozen chart, including filesystem aliases."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from file_outputs import ensure_distinct_output


class FrozenOutputChecks(unittest.TestCase):
    def test_both_cli_commands_reject_output_equal_to_input_and_preserve_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            chart = Path(directory) / "chart.json"
            original = (ROOT / "evals/fixtures/base.json").read_bytes()
            for script, extra in (("inspect_patterns.py", []),
                                  ("timing_candidates.py", ["--palaces", "4", "--unit", "day", "--days", "1"])):
                with self.subTest(script=script):
                    chart.write_bytes(original)
                    process = subprocess.run([sys.executable, "-B", str(ROOT / "scripts" / script),
                                              str(chart), *extra, "--output", str(chart)],
                                             capture_output=True, text=True, encoding="utf-8")
                    self.assertNotEqual(process.returncode, 0)
                    self.assertEqual(chart.read_bytes(), original)

    def test_normalized_path_and_hardlink_alias_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            chart = Path(directory) / "chart.json"
            chart.write_bytes(b"frozen-original")
            with self.assertRaises(ValueError):
                ensure_distinct_output(chart, chart.parent / "." / chart.name)
            linked = chart.parent / "chart-hardlink.json"
            os.link(chart, linked)
            with self.assertRaises(ValueError):
                ensure_distinct_output(chart, linked)
            self.assertEqual(chart.read_bytes(), b"frozen-original")

    def test_distinct_derived_file_remains_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            chart = Path(directory) / "chart.json"
            chart.write_bytes(b"frozen-original")
            derived = chart.parent / "patterns.json"
            ensure_distinct_output(chart, derived)
            derived.write_bytes(b"old-derived")
            ensure_distinct_output(chart, derived)
            self.assertNotEqual(hashlib.sha256(chart.read_bytes()).digest(),
                                hashlib.sha256(derived.read_bytes()).digest())


if __name__ == "__main__":
    unittest.main()
