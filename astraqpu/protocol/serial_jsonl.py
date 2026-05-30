from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json
import time

from astraqpu.errors import AstraQPUError
from astraqpu.protocol.limits import (
    MAX_DEVICE_EVENT_NAME_CHARS,
    MAX_DEVICE_OP_CHARS,
    MAX_JSON_LINE_BYTES,
    MAX_JOB_ID_CHARS,
    MAX_TRACE_EVENTS,
    PROTOCOL,
)
from astraqpu.runtime import ExecutionTrace, TraceEvent
from astraqpu.scheduler import ScheduledProgram


@dataclass(frozen=True)
class SerialEvent:
    kind: str
    payload: dict[str, Any]


def encode_json_line(message: dict[str, Any]) -> bytes:
    return (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")


def decode_json_line(line: bytes | str) -> dict[str, Any]:
    if isinstance(line, bytes) and len(line) > MAX_JSON_LINE_BYTES:
        raise AstraQPUError(f"received serial line longer than {MAX_JSON_LINE_BYTES} bytes")
    if isinstance(line, bytes):
        line = line.decode("utf-8")
    if len(line.encode("utf-8")) > MAX_JSON_LINE_BYTES:
        raise AstraQPUError(f"received serial line longer than {MAX_JSON_LINE_BYTES} bytes")
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
            if instruction.op == "set_reg":
                metadata = message.pop("metadata", {})
                message["register"] = metadata.get("name")
                message["value"] = str(metadata.get("value", ""))
            messages.append(message)
        messages.append({"type": "RUN", "proto": PROTOCOL, "job_id": self.job_id})
        return messages

    def host_lines(self, program: ScheduledProgram) -> list[bytes]:
        return [encode_json_line(message) for message in self.host_messages(program)]

    def parse_device_message(self, message: dict[str, Any]) -> SerialEvent:
        message_type = str(message.get("type", "")).upper()
        if message_type == "HELLO":
            _require_fields(message, ("proto", "device"))
            if message.get("proto") != PROTOCOL:
                raise AstraQPUError(f"device protocol mismatch: expected {PROTOCOL}, got {message.get('proto')!r}")
            return SerialEvent("hello", message)
        if message_type == "ACK":
            _require_fields(message, ("job_id",))
            _check_text(message, "job_id", MAX_JOB_ID_CHARS)
            return SerialEvent("ack", message)
        if message_type == "NACK":
            _require_fields(message, ("job_id", "reason"))
            _check_text(message, "job_id", MAX_JOB_ID_CHARS)
            raise AstraQPUError(f"device rejected command: {message}")
        if message_type == "EVT":
            _require_fields(message, ("job_id", "event", "id", "op"))
            _check_text(message, "job_id", MAX_JOB_ID_CHARS)
            _check_text(message, "event", MAX_DEVICE_EVENT_NAME_CHARS)
            _check_text(message, "op", MAX_DEVICE_OP_CHARS)
            _check_int(message, "id")
            if "t_ns" not in message and "t_us" not in message:
                raise AstraQPUError("device EVT message requires t_ns or t_us")
            return SerialEvent("event", message)
        if message_type == "RESULT":
            _require_fields(message, ("job_id", "bits"))
            _check_text(message, "job_id", MAX_JOB_ID_CHARS)
            if not isinstance(message["bits"], dict):
                raise AstraQPUError("device RESULT bits must be a JSON object")
            return SerialEvent("result", message)
        if message_type == "DONE":
            _require_fields(message, ("job_id",))
            _check_text(message, "job_id", MAX_JOB_ID_CHARS)
            return SerialEvent("done", message)
        if message_type == "TELEM":
            _require_fields(message, ("job_id",))
            _check_text(message, "job_id", MAX_JOB_ID_CHARS)
            return SerialEvent("telemetry", message)
        raise AstraQPUError(f"unknown device serial message type: {message_type!r}")

    def trace_from_events(self, architecture: str, events: list[SerialEvent]) -> ExecutionTrace:
        trace_events: list[TraceEvent] = []
        for event in events:
            if event.kind != "event":
                continue
            if len(trace_events) >= MAX_TRACE_EVENTS:
                raise AstraQPUError(f"device emitted more than {MAX_TRACE_EVENTS} trace events")
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
                    metadata=_event_metadata(payload),
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


def _event_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {"source": "mcu"}
    for key in ("register", "value", "flag", "severity"):
        if key in payload:
            metadata[key] = payload[key]
    return metadata


def _require_fields(message: dict[str, Any], fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if field not in message]
    if missing:
        raise AstraQPUError(f"device {message.get('type', '<missing type>')} message missing fields: {', '.join(missing)}")


def _check_text(message: dict[str, Any], field: str, limit: int) -> None:
    value = message[field]
    if not isinstance(value, str):
        raise AstraQPUError(f"device {message.get('type')} field {field} must be a string")
    if len(value) > limit:
        raise AstraQPUError(f"device {message.get('type')} field {field} is longer than {limit} characters")


def _check_int(message: dict[str, Any], field: str) -> None:
    value = message[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise AstraQPUError(f"device {message.get('type')} field {field} must be an integer")
