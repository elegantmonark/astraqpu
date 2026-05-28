from __future__ import annotations

from astraqpu.runtime import ExecutionTrace, TraceEvent
from astraqpu.scheduler import ScheduledProgram


class VirtualBackend:
    name = "akasha.virtual"

    def run(self, program: ScheduledProgram) -> ExecutionTrace:
        events: list[TraceEvent] = []

        for instruction in program.instructions:
            metadata = _metadata(instruction)
            events.append(
                TraceEvent(
                    t_ns=instruction.t_ns,
                    event="instruction_start",
                    instruction_id=instruction.id,
                    op=instruction.op,
                    qubits=instruction.qubits,
                    bits=instruction.bits,
                    metadata=metadata,
                )
            )
            events.append(
                TraceEvent(
                    t_ns=instruction.t_ns + instruction.duration_ns,
                    event="instruction_end",
                    instruction_id=instruction.id,
                    op=instruction.op,
                    qubits=instruction.qubits,
                    bits=instruction.bits,
                    metadata=metadata,
                )
            )
            if instruction.latency_ns:
                events.append(
                    TraceEvent(
                        t_ns=instruction.end_ns,
                        event="latency_complete",
                        instruction_id=instruction.id,
                        op=instruction.op,
                        qubits=instruction.qubits,
                        bits=instruction.bits,
                        metadata=metadata,
                    )
                )

        return ExecutionTrace(
            architecture=program.architecture,
            backend=self.name,
            events=tuple(sorted(events, key=lambda e: (e.t_ns, e.instruction_id, _event_order(e.event)))),
        )


def _metadata(instruction) -> dict | None:
    if instruction.gate:
        return {"gate": instruction.gate}
    if instruction.op == "set_reg":
        return dict(instruction.metadata)
    return None


def _event_order(event: str) -> int:
    order = {
        "instruction_start": 0,
        "instruction_end": 1,
        "latency_complete": 2,
    }
    return order.get(event, 99)
