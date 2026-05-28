import unittest
from pathlib import Path

from astraqpu.arch import load_architecture
from astraqpu.frontend import parse_sutra_file
from astraqpu.protocol import SerialProtocol, decode_json_line
from astraqpu.protocol.serial_jsonl import PROTOCOL, SerialSession
from astraqpu.scheduler import schedule_program


ROOT = Path(__file__).resolve().parents[1]


class FakeTransport:
    def __init__(self, responses):
        self.writes = []
        self.responses = list(responses)

    def write(self, line):
        self.writes.append(line)

    def readline(self):
        if not self.responses:
            return b""
        return self.responses.pop(0)


class SerialProtocolTests(unittest.TestCase):
    def scheduled_bell(self):
        arch = load_architecture(ROOT / "examples" / "arch" / "tiny_3q.json")
        program = parse_sutra_file(ROOT / "examples" / "bell.aqis")
        return schedule_program(program, arch)

    def test_host_messages_include_load_instructions_and_run(self):
        scheduled = self.scheduled_bell()
        messages = SerialProtocol(job_id="bell_001").host_messages(scheduled)

        self.assertEqual(messages[0]["type"], "HELLO")
        self.assertEqual(messages[0]["proto"], PROTOCOL)
        self.assertEqual(messages[1]["type"], "LOAD")
        self.assertEqual(messages[1]["instruction_count"], 6)
        self.assertEqual(messages[-1]["type"], "RUN")
        inst_messages = [message for message in messages if message["type"] == "INST"]
        self.assertEqual(len(inst_messages), 6)
        self.assertEqual(inst_messages[2]["gate"], "h")

    def test_json_line_round_trip(self):
        line = SerialProtocol(job_id="bell_001").host_lines(self.scheduled_bell())[0]
        message = decode_json_line(line)

        self.assertEqual(message["type"], "HELLO")
        self.assertEqual(message["proto"], PROTOCOL)

    def test_serial_session_builds_trace_from_device_events(self):
        scheduled = self.scheduled_bell()
        responses = [
            b'{"type":"HELLO","proto":"astraqpu.serial.v0","device":"fake"}\n',
            b'{"type":"ACK","job_id":"bell_001","command":"LOAD"}\n',
            b'{"type":"EVT","job_id":"bell_001","event":"instruction_start","id":1,"op":"prep","t_ns":0}\n',
            b'{"type":"EVT","job_id":"bell_001","event":"instruction_end","id":1,"op":"prep","t_ns":20}\n',
            b'{"type":"DONE","job_id":"bell_001"}\n',
        ]
        transport = FakeTransport(responses)

        trace = SerialSession(transport, SerialProtocol(job_id="bell_001"), timeout_s=0.1).run(scheduled)

        self.assertGreater(len(transport.writes), 0)
        self.assertEqual(trace.backend, "yantra.serial")
        self.assertEqual(len(trace.events), 2)
        self.assertEqual(trace.events[1].t_ns, 20)

    def test_set_reg_is_flattened_for_the_mcu(self):
        arch = load_architecture(ROOT / "examples" / "arch" / "tiny_3q.json")
        program = parse_sutra_file(ROOT / "examples" / "calibration_pulse.aqis")
        scheduled = schedule_program(program, arch)

        messages = SerialProtocol(job_id="cal_001").host_messages(scheduled)
        set_reg = next(message for message in messages if message.get("op") == "set_reg")

        self.assertEqual(set_reg["register"], "q0.drive_amp")
        self.assertEqual(set_reg["value"], "0.42")

    def test_register_events_keep_register_metadata(self):
        event = SerialProtocol(job_id="cal_001").parse_device_message(
            {
                "type": "EVT",
                "job_id": "cal_001",
                "event": "register_set",
                "id": 1,
                "op": "set_reg",
                "register": "q0.drive_amp",
                "value": "0.42",
                "t_ns": 0,
            }
        )

        trace = SerialProtocol(job_id="cal_001").trace_from_events("tiny", [event])

        self.assertEqual(trace.events[0].metadata["register"], "q0.drive_amp")
        self.assertEqual(trace.events[0].metadata["value"], "0.42")


if __name__ == "__main__":
    unittest.main()
