from pathlib import Path
import unittest

from astraqpu.arch import load_architecture
from astraqpu.backends import VirtualBackend
from astraqpu.frontend import parse_sutra_file
from astraqpu.scheduler import schedule_program


ROOT = Path(__file__).resolve().parents[1]


class VirtualBackendTests(unittest.TestCase):
    def test_virtual_backend_emits_trace_events(self):
        arch = load_architecture(ROOT / "examples" / "arch" / "tiny_3q.json")
        program = parse_sutra_file(ROOT / "examples" / "bell.aqis")
        scheduled = schedule_program(program, arch)

        trace = VirtualBackend().run(scheduled)
        data = trace.to_dict()

        self.assertEqual(data["format"], "astraqpu.trace.v0")
        self.assertEqual(data["backend"], "akasha.virtual")
        self.assertTrue(any(event["event"] == "latency_complete" for event in data["events"]))


if __name__ == "__main__":
    unittest.main()
