from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from astraqpu.arch import ArchitectureSpec
from astraqpu.errors import ScheduleError
from astraqpu.ir import Instruction, Program


@dataclass(frozen=True)
class ScheduledInstruction:
    id: int
    t_ns: int
    op: str
    qubits: tuple[str, ...] = ()
    bits: tuple[str, ...] = ()
    gate: str | None = None
    duration_ns: int = 0
    latency_ns: int = 0
    channels: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def end_ns(self) -> int:
        return self.t_ns + self.duration_ns + self.latency_ns

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "t_ns": self.t_ns,
            "op": self.op,
            "qubits": list(self.qubits),
            "bits": list(self.bits),
            "duration_ns": self.duration_ns,
            "latency_ns": self.latency_ns,
            "channels": list(self.channels),
        }
        if self.gate is not None:
            data["gate"] = self.gate
        if self.metadata:
            data["metadata"] = self.metadata
        return data


@dataclass(frozen=True)
class ScheduledProgram:
    architecture: str
    tick_ns: int
    instructions: tuple[ScheduledInstruction, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "astraqpu.scheduled.v0",
            "architecture": self.architecture,
            "tick_ns": self.tick_ns,
            "instructions": [instruction.to_dict() for instruction in self.instructions],
        }


def schedule_program(program: Program, arch: ArchitectureSpec) -> ScheduledProgram:
    declared = program.declared_qubit_names()
    if not declared.issubset(set(arch.qubits)):
        missing = sorted(declared - set(arch.qubits))
        raise ScheduleError(f"program declares qubits not present in architecture: {', '.join(missing)}")

    qubit_available = {qubit: 0 for qubit in arch.qubits}
    channel_available: dict[str, int] = {}
    global_floor = 0
    scheduled: list[ScheduledInstruction] = []

    for index, instruction in enumerate(program.instructions, start=1):
        if instruction.op == "wait":
            start = _round_to_tick(max([global_floor, *qubit_available.values(), *channel_available.values()]), arch.tick_ns)
            duration = _round_duration(instruction.duration_ns or 0, arch.tick_ns)
            global_floor = start + duration
            scheduled.append(ScheduledInstruction(id=index, t_ns=start, op="wait", duration_ns=duration))
            continue

        if instruction.op == "barrier":
            arch.require_qubits(instruction.qubits)
            start = _round_to_tick(max([global_floor, *(qubit_available[q] for q in instruction.qubits)]), arch.tick_ns)
            for qubit in instruction.qubits:
                qubit_available[qubit] = start
            scheduled.append(ScheduledInstruction(id=index, t_ns=start, op="barrier", qubits=instruction.qubits))
            continue

        if instruction.op == "set_reg":
            scheduled.append(
                ScheduledInstruction(
                    id=index,
                    t_ns=_round_to_tick(global_floor, arch.tick_ns),
                    op="set_reg",
                    metadata={"name": instruction.name, "value": instruction.value},
                )
            )
            continue

        op_name = _operation_name(instruction)
        arch.require_qubits(instruction.qubits)
        operation = arch.require_operation(op_name)
        _validate_topology(instruction, arch)
        channels = arch.resolve_channels(operation, instruction.qubits)
        start = _earliest_start(instruction, channels, global_floor, qubit_available, channel_available, arch.tick_ns)
        duration = _round_duration(operation.duration_ns, arch.tick_ns)
        latency = _round_duration(operation.latency_ns, arch.tick_ns)
        end = start + duration + latency

        for qubit in instruction.qubits:
            qubit_available[qubit] = end
        for channel in channels:
            channel_available[channel] = start + duration

        scheduled.append(
            ScheduledInstruction(
                id=index,
                t_ns=start,
                op=instruction.op,
                gate=instruction.gate,
                qubits=instruction.qubits,
                bits=instruction.bits,
                duration_ns=duration,
                latency_ns=latency,
                channels=channels,
            )
        )

    return ScheduledProgram(architecture=arch.name, tick_ns=arch.tick_ns, instructions=tuple(scheduled))


def _operation_name(instruction: Instruction) -> str:
    if instruction.op == "gate":
        if instruction.gate is None:
            raise ScheduleError("gate instruction is missing a gate name")
        return instruction.gate
    return instruction.op


def _validate_topology(instruction: Instruction, arch: ArchitectureSpec) -> None:
    if instruction.op != "gate" or len(instruction.qubits) != 2:
        return
    q0, q1 = instruction.qubits
    if not arch.supports_coupling(q0, q1):
        raise ScheduleError(f"gate {instruction.gate!r} cannot run on uncoupled qubits {q0}, {q1}")


def _earliest_start(
    instruction: Instruction,
    channels: tuple[str, ...],
    global_floor: int,
    qubit_available: dict[str, int],
    channel_available: dict[str, int],
    tick_ns: int,
) -> int:
    candidates = [global_floor]
    candidates.extend(qubit_available[qubit] for qubit in instruction.qubits)
    candidates.extend(channel_available.get(channel, 0) for channel in channels)
    return _round_to_tick(max(candidates), tick_ns)


def _round_to_tick(value: int, tick_ns: int) -> int:
    remainder = value % tick_ns
    if remainder == 0:
        return value
    return value + tick_ns - remainder


def _round_duration(value: int, tick_ns: int) -> int:
    if value == 0:
        return 0
    return _round_to_tick(value, tick_ns)

