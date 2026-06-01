import unittest
from pathlib import Path

from astraqpu.runtime import ExecutionTrace, TraceEvent
from astraqpu.runtime.compare import compare_traces, load_trace


ROOT = Path(__file__).resolve().parents[1]


class TraceCompareTests(unittest.TestCase):
    def test_compare_passes_when_events_are_inside_tolerance(self):
        expected = ExecutionTrace(
            architecture="tiny",
            backend="akasha.virtual",
            events=(
                TraceEvent(t_ns=100, event="instruction_start", instruction_id=1, op="prep"),
                TraceEvent(t_ns=120, event="instruction_end", instruction_id=1, op="prep"),
            ),
        )
        observed = ExecutionTrace(
            architecture="tiny",
            backend="yantra.serial",
            events=(
                TraceEvent(t_ns=110, event="instruction_start", instruction_id=1, op="prep"),
                TraceEvent(t_ns=115, event="instruction_end", instruction_id=1, op="prep"),
            ),
        )

        report = compare_traces(expected, observed, tolerance_ns=10)

        self.assertEqual(report.status, "pass")
        self.assertEqual(report.matches[0].status, "ok")

    def test_compare_reports_late_missing_and_unexpected_events(self):
        expected = ExecutionTrace(
            architecture="tiny",
            backend="akasha.virtual",
            events=(
                TraceEvent(t_ns=100, event="instruction_start", instruction_id=1, op="prep"),
                TraceEvent(t_ns=120, event="instruction_end", instruction_id=1, op="prep"),
            ),
        )
        observed = ExecutionTrace(
            architecture="tiny",
            backend="yantra.serial",
            events=(
                TraceEvent(t_ns=160, event="instruction_start", instruction_id=1, op="prep"),
                TraceEvent(t_ns=200, event="instruction_start", instruction_id=9, op="device"),
            ),
        )

        report = compare_traces(expected, observed, tolerance_ns=10)
        data = report.to_dict()

        self.assertEqual(report.status, "fail")
        self.assertEqual(report.matches[0].status, "late")
        self.assertEqual(len(report.missing), 1)
        self.assertEqual(len(report.unexpected), 1)
        self.assertEqual(data["summary"]["late_or_early"], 1)

    def test_summary_text_includes_status_counts_and_worst_drift(self):
        expected = ExecutionTrace(
            architecture="tiny",
            backend="akasha.virtual",
            events=(
                TraceEvent(t_ns=100, event="instruction_start", instruction_id=1, op="prep"),
                TraceEvent(t_ns=120, event="instruction_end", instruction_id=1, op="prep"),
            ),
        )
        observed = ExecutionTrace(
            architecture="tiny",
            backend="yantra.serial",
            events=(
                TraceEvent(t_ns=160, event="instruction_start", instruction_id=1, op="prep"),
            ),
        )

        summary = compare_traces(expected, observed, tolerance_ns=10).to_summary_text()

        self.assertIn("status: fail", summary)
        self.assertIn("late or early: 1", summary)
        self.assertIn("missing: 1", summary)
        self.assertIn("worst drift:", summary)

    def test_load_trace_reads_trace_json(self):
        trace = load_trace(ROOT / "examples" / "traces" / "bell_expected.trace.json")

        self.assertEqual(trace.backend, "akasha.virtual")
        self.assertEqual(len(trace.events), 3)


if __name__ == "__main__":
    unittest.main()
