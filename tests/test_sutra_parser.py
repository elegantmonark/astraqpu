import unittest

from astraqpu.frontend import parse_sutra


class SutraParserTests(unittest.TestCase):
    def test_parse_bell_program(self):
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

        self.assertEqual(program.declared_qubits, 2)
        self.assertEqual(program.declared_bits, 2)
        self.assertEqual(
            [instruction.op for instruction in program.instructions],
            ["prep", "prep", "gate", "gate", "measure", "measure"],
        )
        self.assertEqual(program.instructions[2].gate, "h")
        self.assertEqual(program.instructions[3].qubits, ("q0", "q1"))

    def test_wait_duration_parses_to_nanoseconds(self):
        program = parse_sutra(
            """
            DECLARE_QUBITS 1
            DECLARE_BITS 1
            WAIT 3us
            END
            """
        )

        self.assertEqual(program.instructions[0].duration_ns, 3000)


if __name__ == "__main__":
    unittest.main()
