from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json
import time

from astraqpu.errors import AstraQPUError
from astraqpu.runtime import ExecutionTrace, TraceEvent
from astraqpu.scheduler import ScheduledProgram


PROTOCOL = "astraqpu.serial.v0"


@dataclass(frozen=True)
class SerialEvent:
    kind: str
    payload: dict[str, Any]


def encode_json_line(message: dict[str, Any]) -> bytes:
    return (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")


def decode_json_line(line: bytes | str) -> dict[str, Any]:
    if isinstance(line, bytes):
        line = line.decode("utf-8")
    line = line.strip()
    if not line:
        raise AstraQPUError("received empty serial line")
    try:
        message = json.loads(line)
    except json.JSONDecodeError as exc:
        raise AstraQPUError(f"received invalid serial JSON: {line!r}") from exc
    if not isinstance(message, dict):
        raise AstraQPUError("received serial message that is not a JSON object")
    return message


class SerialProtocol:
    """JSON Lines protocol used between the host runtime and MCU control unit."""

    def __init__(self, job_id: str = "job_001") -> None:
        self.job_id = job_id

    def host_messages(self, program: ScheduledProgram) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [
            {"type": "HELLO", "proto": PROTOCOL, "host": "astraqpu"},
            {
                "type": "LOAD",
                "proto": PROTOCOL,
                "job_id": self.job_id,
                "architecture": program.architecture,
                "tick_ns": program.tick_ns,
                "instruction_count": len(program.instructions),
            },
        ]
        for instruction in program.instructions:
            message = {"type": "INST", "proto": PROTOCOL, "job_id": self.job_id}
            message.update(instruction.to_dict())
            messages.append(message)
        messages.append({"type": "RUN", "proto": PROTOCOL, "job_id": self.job_id})
        return messages

    def host_lines(self, program: ScheduledProgram) -> list[bytes]:
        return [encode_json_line(message) for message in self.host_messages(program)]

    def parse_device_message(self, message: dict[str, Any]) -> SerialEvent:
        message_type = str(message.get("type", "")).upper()
        if message_type == "HELLO":
            if message.get("proto") != PROTOCOL:
                raise AstraQPUError(f"device protocol mismatch: expected {PROTOCOL}, got {message.get('proto')!r}")
            return SerialEvent("hello", message)
        if message_type == "ACK":
            return SerialEvent("ack", message)
        if message_type == "NACK":
            raise AstraQPUError(f"device rejected command: {message}")
        if message_type == "EVT":
            return SerialEvent("event", message)
        if message_type == "RESULT":
            return SerialEvent("result", message)
        if message_type == "DONE":
            return SerialEvent("done", message)
        if message_type == "TELEM":
            return SerialEvent("telemetry", message)
        raise AstraQPUError(f"unknown device serial message type: {message_type!r}")

    def trace_from_events(self, architecture: str, events: list[SerialEvent]) -> ExecutionTrace:
        trace_events: list[TraceEvent] = []
        for event in events:
            if event.kind != "event":
                continue
            payload = event.payload
            t_ns = _event_time_ns(payload)
            trace_events.append(
                TraceEvent(
                    t_ns=t_ns,
                    event=str(payload.get("event", "device_event")),
                    instruction_id=int(payload.get("id", payload.get("instruction_id", 0))),
                    op=str(payload.get("op", "device")),
                    qubits=tuple(payload.get("qubits", ())),
                    bits=tuple(payload.get("bits", ())),
                    metadata={"source": "mcu"},
                )
            )
        return ExecutionTrace(architecture=architecture, backend="yantra.serial", events=tuple(trace_events))


class SerialSession:
    """Synchronous serial session over a line-oriented transport."""

    def __init__(
        self,
        transport: Any,
        protocol: SerialProtocol,
        timeout_s: float = 10.0,
        inter_write_delay_s: float = 0.0,
    ) -> None:
        self.transport = transport
        self.protocol = protocol
        self.timeout_s = timeout_s
        self.inter_write_delay_s = inter_write_delay_s

    def run(self, program: ScheduledProgram) -> ExecutionTrace:
        for line in self.protocol.host_lines(program):
            self.transport.write(line)
            flush = getattr(self.transport, "flush", None)
            if flush is not None:
                flush()
            if self.inter_write_delay_s > 0:
                time.sleep(self.inter_write_delay_s)

        events: list[SerialEvent] = []
        deadline = time.monotonic() + self.timeout_s
        while time.monotonic() < deadline:
            raw = self.transport.readline()
            if not raw:
                continue
            event = self.protocol.parse_device_message(decode_json_line(raw))
            events.append(event)
            if event.kind in {"result", "done"}:
                break

        if not any(event.kind in {"result", "done"} for event in events):
            raise AstraQPUError("serial session timed out before RESULT or DONE")
        return self.protocol.trace_from_events(program.architecture, events)


def _event_time_ns(payload: dict[str, Any]) -> int:
    if "t_ns" in payload:
        return int(payload["t_ns"])
    if "t_us" in payload:
        return int(payload["t_us"]) * 1000
    return 0
