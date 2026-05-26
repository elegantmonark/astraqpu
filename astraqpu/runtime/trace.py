from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TraceEvent:
    t_ns: int
    event: str
    instruction_id: int
    op: str
    qubits: tuple[str, ...] = ()
    bits: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "t_ns": self.t_ns,
            "event": self.event,
            "instruction_id": self.instruction_id,
            "op": self.op,
            "qubits": list(self.qubits),
            "bits": list(self.bits),
        }
        if self.metadata:
            data["metadata"] = self.metadata
        return data


@dataclass(frozen=True)
class ExecutionTrace:
    architecture: str
    backend: str
    events: tuple[TraceEvent, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "astraqpu.trace.v0",
            "architecture": self.architecture,
            "backend": self.backend,
            "events": [event.to_dict() for event in self.events],
        }

