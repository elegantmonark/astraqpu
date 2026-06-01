import unittest
from pathlib import Path

from astraqpu.arch import load_architecture
from astraqpu.frontend import parse_sutra_file
from astraqpu.scheduler import schedule_program, summarize_timeline


ROOT = Path(__file__).resolve().parents[1]


class TimelineTests(unittest.TestCase):
    def test_timeline_summary_reports_duration_counts_and_occupancy(self):
        arch = load_architecture(ROOT / "examples" / "arch" / "tiny_3q.json")
        program = parse_sutra_file(ROOT / "examples" / "bell.aqis")
        scheduled = schedule_program(program, arch)

        summary = summarize_timeline(scheduled).to_dict()

        self.assertEqual(summary["format"], "astraqpu.timeline.v0")
        self.assertEqual(summary["total_duration_ns"], 6560)
        self.assertEqual(summary["instruction_count"], 6)
        self.assertEqual(summary["op_counts"]["measure"], 2)
        self.assertIn("drive:q0", summary["channel_occupancy"])
        self.assertIn("readout:q1", summary["channel_occupancy"])
        self.assertIn("q0", summary["qubit_occupancy"])

    def test_zero_duration_registers_do_not_create_occupancy_windows(self):
        arch = load_architecture(ROOT / "examples" / "arch" / "tiny_3q.json")
        program = parse_sutra_file(ROOT / "examples" / "calibration_pulse.aqis")
        scheduled = schedule_program(program, arch)

        summary = summarize_timeline(scheduled).to_dict()

        self.assertEqual(summary["op_counts"]["set_reg"], 3)
        self.assertNotIn("set_reg", {window["op"] for windows in summary["channel_occupancy"].values() for window in windows})


if __name__ == "__main__":
    unittest.main()

