from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from astraqpu.scheduler.scheduler import ScheduledInstruction, ScheduledProgram


@dataclass(frozen=True)
class OccupancyWindow:
    resource: str
    instruction_id: int
    op: str
    start_ns: int
    end_ns: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource": self.resource,
            "instruction_id": self.instruction_id,
            "op": self.op,
            "start_ns": self.start_ns,
            "end_ns": self.end_ns,
            "duration_ns": self.end_ns - self.start_ns,
        }


@dataclass(frozen=True)
class TimelineSummary:
    architecture: str
    tick_ns: int
    total_duration_ns: int
    instruction_count: int
    op_counts: dict[str, int]
    channel_occupancy: dict[str, tuple[OccupancyWindow, ...]]
    qubit_occupancy: dict[str, tuple[OccupancyWindow, ...]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "astraqpu.timeline.v0",
            "architecture": self.architecture,
            "tick_ns": self.tick_ns,
            "total_duration_ns": self.total_duration_ns,
            "instruction_count": self.instruction_count,
            "op_counts": self.op_counts,
            "channel_occupancy": _windows_to_dict(self.channel_occupancy),
            "qubit_occupancy": _windows_to_dict(self.qubit_occupancy),
        }


def summarize_timeline(program: ScheduledProgram) -> TimelineSummary:
    channel_occupancy: dict[str, list[OccupancyWindow]] = {}
    qubit_occupancy: dict[str, list[OccupancyWindow]] = {}
    op_counts: dict[str, int] = {}
    total_duration_ns = 0

    for instruction in program.instructions:
        op_counts[instruction.op] = op_counts.get(instruction.op, 0) + 1
        total_duration_ns = max(total_duration_ns, instruction.end_ns)
        _add_channel_windows(channel_occupancy, instruction)
        _add_qubit_windows(qubit_occupancy, instruction)

    return TimelineSummary(
        architecture=program.architecture,
        tick_ns=program.tick_ns,
        total_duration_ns=total_duration_ns,
        instruction_count=len(program.instructions),
        op_counts=op_counts,
        channel_occupancy={key: tuple(value) for key, value in sorted(channel_occupancy.items())},
        qubit_occupancy={key: tuple(value) for key, value in sorted(qubit_occupancy.items())},
    )


def _add_channel_windows(target: dict[str, list[OccupancyWindow]], instruction: ScheduledInstruction) -> None:
    end_ns = instruction.t_ns + instruction.duration_ns
    if end_ns == instruction.t_ns:
        return
    for channel in instruction.channels:
        target.setdefault(channel, []).append(_window(channel, instruction, end_ns))


def _add_qubit_windows(target: dict[str, list[OccupancyWindow]], instruction: ScheduledInstruction) -> None:
    if instruction.end_ns == instruction.t_ns:
        return
    for qubit in instruction.qubits:
        target.setdefault(qubit, []).append(_window(qubit, instruction, instruction.end_ns))


def _window(resource: str, instruction: ScheduledInstruction, end_ns: int) -> OccupancyWindow:
    return OccupancyWindow(
        resource=resource,
        instruction_id=instruction.id,
        op=instruction.op,
        start_ns=instruction.t_ns,
        end_ns=end_ns,
    )


def _windows_to_dict(groups: dict[str, tuple[OccupancyWindow, ...]]) -> dict[str, list[dict[str, Any]]]:
    return {
        resource: [window.to_dict() for window in windows]
        for resource, windows in groups.items()
    }

