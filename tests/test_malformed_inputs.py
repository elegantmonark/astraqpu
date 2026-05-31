import json
import tempfile
import unittest
from pathlib import Path

from astraqpu.arch import load_architecture
from astraqpu.arch.spec import architecture_from_dict
from astraqpu.errors import ArchitectureError, AstraQPUError, ParseError
from astraqpu.frontend import parse_sutra
from astraqpu.protocol import decode_json_line
from astraqpu.runtime.compare import load_trace


class MalformedInputTests(unittest.TestCase):
    def test_parser_rejects_undeclared_qubit(self):
        with self.assertRaises(ParseError):
            parse_sutra(
                """
                DECLARE_QUBITS 1
                DECLARE_BITS 1
                GATE H q2
                END
                """
            )

    def test_parser_rejects_bad_register_name(self):
        with self.assertRaises(ParseError):
            parse_sutra(
                """
                DECLARE_QUBITS 1
                DECLARE_BITS 1
                SET_REG 1bad.name 0.4
                END
                """
            )

    def test_architecture_rejects_missing_required_gate(self):
        with self.assertRaises(ArchitectureError):
            architecture_from_dict(
                {
                    "name": "bad",
                    "clock": {"tick_ns": 10},
                    "qubits": {"q0": {}},
                    "native_gates": {
                        "prep": {"duration_ns": 10, "channels": []},
                    },
                }
            )

    def test_architecture_rejects_invalid_json_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{not-json", encoding="utf-8")

            with self.assertRaises(ArchitectureError):
                load_architecture(path)

    def test_serial_decode_rejects_non_object_json(self):
        with self.assertRaises(AstraQPUError):
            decode_json_line("[1, 2, 3]")

    def test_trace_loader_rejects_wrong_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.trace.json"
            path.write_text(json.dumps({"format": "not.astraqpu"}), encoding="utf-8")

            with self.assertRaises(AstraQPUError):
                load_trace(path)


if __name__ == "__main__":
    unittest.main()
