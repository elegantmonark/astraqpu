import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from astraqpu.cli import main


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_trace_compare_returns_failure_on_mismatch(self):
        with redirect_stdout(StringIO()):
            code = main(
                [
                    "trace-compare",
                    "--expected",
                    str(ROOT / "examples" / "traces" / "bell_expected.trace.json"),
                    "--observed",
                    str(ROOT / "examples" / "traces" / "bell_observed_drift.trace.json"),
                    "--tolerance-ns",
                    "100",
                ]
            )

        self.assertEqual(code, 1)

    def test_trace_compare_allow_mismatch_returns_success(self):
        with redirect_stdout(StringIO()):
            code = main(
                [
                    "trace-compare",
                    "--expected",
                    str(ROOT / "examples" / "traces" / "bell_expected.trace.json"),
                    "--observed",
                    str(ROOT / "examples" / "traces" / "bell_observed_drift.trace.json"),
                    "--tolerance-ns",
                    "100",
                    "--allow-mismatch",
                ]
            )

        self.assertEqual(code, 0)

    def test_trace_compare_summary_format_prints_text(self):
        output = StringIO()
        with redirect_stdout(output):
            code = main(
                [
                    "trace-compare",
                    "--expected",
                    str(ROOT / "examples" / "traces" / "bell_expected.trace.json"),
                    "--observed",
                    str(ROOT / "examples" / "traces" / "bell_observed_drift.trace.json"),
                    "--tolerance-ns",
                    "100",
                    "--allow-mismatch",
                    "--format",
                    "summary",
                ]
            )

        self.assertEqual(code, 0)
        self.assertIn("AstraQPU trace compare", output.getvalue())
        self.assertIn("status: fail", output.getvalue())


if __name__ == "__main__":
    unittest.main()
