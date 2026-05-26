from pathlib import Path
import unittest

from astraqpu.arch import load_architecture
from astraqpu.errors import ScheduleError
from astraqpu.frontend import parse_sutra
from astraqpu.scheduler import schedule_program


ROOT = Path(__file__).resolve().parents[1]
ARCH = ROOT / "examples" / "arch" / "tiny_3q.json"


class SchedulerTests(unittest.TestCase):
    def test_bell_schedule_respects_dependencies_and_latency(self):
        arch = load_architecture(ARCH)
        program = parse_sutra(
            """
            DECLARE_QUBITS 2
            DECLARE_BITS 2
            PREP q0
            PREP q1
            GATE H q0
            GATE CX q0 q1
            MEASURE q0 -> c0
            MEASURE q1 -> c1
            END
            """
        )

        scheduled = schedule_program(program, arch)
        by_id = {instruction.id: instruction for instruction in scheduled.instructions}

        self.assertEqual(by_id[1].t_ns, 0)
        self.assertEqual(by_id[2].t_ns, 0)
        self.assertEqual(by_id[3].t_ns, 20)
        self.assertEqual(by_id[4].t_ns, 60)
        self.assertEqual(by_id[5].t_ns, 360)
        self.assertEqual(by_id[6].t_ns, 360)
        self.assertEqual(by_id[5].latency_ns, 5000)

    def test_uncoupled_two_qubit_gate_is_rejected(self):
        arch = load_architecture(ARCH)
        program = parse_sutra(
            """
            DECLARE_QUBITS 3
            DECLARE_BITS 1
            GATE CX q0 q2
            END
            """
        )

        with self.assertRaises(ScheduleError):
            schedule_program(program, arch)


if __name__ == "__main__":
    unittest.main()
