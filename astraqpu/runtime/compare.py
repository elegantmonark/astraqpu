from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

from astraqpu.errors import AstraQPUError
from astraqpu.runtime import ExecutionTrace, TraceEvent


MATCH_EVENTS = {"instruction_start", "instruction_end", "latency_complete", "register_set"}


@dataclass(frozen=True)
class TraceMatch:
    instruction_id: int
    event: str
    expected_t_ns: int
    observed_t_ns: int
    drift_ns: int
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "instruction_id": self.instruction_id,
            "event": self.event,
            "expected_t_ns": self.expected_t_ns,
            "observed_t_ns": self.observed_t_ns,
            "drift_ns": self.drift_ns,
            "status": self.status,
        }


@dataclass(frozen=True)
class TraceMissing:
    instruction_id: int
    event: str
    expected_t_ns: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "instruction_id": self.instruction_id,
            "event": self.event,
            "expected_t_ns": self.expected_t_ns,
        }


@dataclass(frozen=True)
class TraceUnexpected:
    instruction_id: int
    event: str
    observed_t_ns: int
    op: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "instruction_id": self.instruction_id,
            "event": self.event,
            "observed_t_ns": self.observed_t_ns,
            "op": self.op,
        }


@dataclass(frozen=True)
class TraceCompareReport:
    architecture: str
    expected_backend: str
    observed_backend: str
    tolerance_ns: int
    status: str
    matches: tuple[TraceMatch, ...]
    missing: tuple[TraceMissing, ...]
    unexpected: tuple[TraceUnexpected, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "astraqpu.trace_compare.v0",
            "architecture": self.architecture,
            "expected_backend": self.expected_backend,
            "observed_backend": self.observed_backend,
            "tolerance_ns": self.tolerance_ns,
            "status": self.status,
            "summary": {
                "matched": len(self.matches),
                "missing": len(self.missing),
                "unexpected": len(self.unexpected),
                "late_or_early": sum(1 for match in self.matches if match.status != "ok"),
            },
            "matches": [match.to_dict() for match in self.matches],
            "missing": [event.to_dict() for event in self.missing],
            "unexpected": [event.to_dict() for event in self.unexpected],
        }

    def to_summary_text(self) -> str:
        data = self.to_dict()
        summary = data["summary"]
        lines = [
            "AstraQPU trace compare",
            f"status: {self.status}",
            f"architecture: {self.architecture}",
            f"expected backend: {self.expected_backend}",
            f"observed backend: {self.observed_backend}",
            f"tolerance ns: {self.tolerance_ns}",
            "",
            "summary:",
            f"  matched: {summary['matched']}",
            f"  late or early: {summary['late_or_early']}",
            f"  missing: {summary['missing']}",
            f"  unexpected: {summary['unexpected']}",
        ]
        if self.matches:
            worst = max(self.matches, key=lambda match: abs(match.drift_ns))
            lines.extend(
                [
                    "",
                    "worst drift:",
                    f"  instruction: {worst.instruction_id}",
                    f"  event: {worst.event}",
                    f"  drift ns: {worst.drift_ns}",
                    f"  status: {worst.status}",
                ]
            )
        if self.missing:
            lines.extend(["", "missing events:"])
            lines.extend(f"  instruction {event.instruction_id} {event.event} expected at {event.expected_t_ns} ns" for event in self.missing[:5])
        if self.unexpected:
            lines.extend(["", "unexpected events:"])
            lines.extend(f"  instruction {event.instruction_id} {event.event} observed at {event.observed_t_ns} ns" for event in self.unexpected[:5])
        return "\n".join(lines)


def load_trace(path: str | Path) -> ExecutionTrace:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise AstraQPUError(f"could not read trace file {path!r}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise AstraQPUError(f"trace file {path!r} is not valid JSON") from exc
    if data.get("format") != "astraqpu.trace.v0":
        raise AstraQPUError(f"trace file {path!r} is not astraqpu.trace.v0")
    return ExecutionTrace.from_dict(data)


def compare_traces(expected: ExecutionTrace, observed: ExecutionTrace, tolerance_ns: int = 0) -> TraceCompareReport:
    if tolerance_ns < 0:
        raise AstraQPUError("trace compare tolerance must be non negative")

    expected_events = _indexed_events(expected)
    observed_events = _indexed_events(observed)

    matches: list[TraceMatch] = []
    missing: list[TraceMissing] = []
    unexpected: list[TraceUnexpected] = []

    for key, expected_event in expected_events.items():
        observed_event = observed_events.pop(key, None)
        if observed_event is None:
            missing.append(
                TraceMissing(
                    instruction_id=expected_event.instruction_id,
                    event=expected_event.event,
                    expected_t_ns=expected_event.t_ns,
                )
            )
            continue

        drift = observed_event.t_ns - expected_event.t_ns
        matches.append(
            TraceMatch(
                instruction_id=expected_event.instruction_id,
                event=expected_event.event,
                expected_t_ns=expected_event.t_ns,
                observed_t_ns=observed_event.t_ns,
                drift_ns=drift,
                status="ok" if abs(drift) <= tolerance_ns else _drift_status(drift),
            )
        )

    for observed_event in observed_events.values():
        unexpected.append(
            TraceUnexpected(
                instruction_id=observed_event.instruction_id,
                event=observed_event.event,
                observed_t_ns=observed_event.t_ns,
                op=observed_event.op,
            )
        )

    status = "pass"
    if missing or unexpected or any(match.status != "ok" for match in matches):
        status = "fail"

    return TraceCompareReport(
        architecture=expected.architecture,
        expected_backend=expected.backend,
        observed_backend=observed.backend,
        tolerance_ns=tolerance_ns,
        status=status,
        matches=tuple(sorted(matches, key=lambda item: (item.instruction_id, item.event))),
        missing=tuple(sorted(missing, key=lambda item: (item.instruction_id, item.event))),
        unexpected=tuple(sorted(unexpected, key=lambda item: (item.instruction_id, item.event))),
    )


def _indexed_events(trace: ExecutionTrace) -> dict[tuple[int, str], TraceEvent]:
    indexed: dict[tuple[int, str], TraceEvent] = {}
    for event in trace.events:
        if event.event not in MATCH_EVENTS:
            continue
        indexed[(event.instruction_id, event.event)] = event
    return indexed


def _drift_status(drift_ns: int) -> str:
    if drift_ns > 0:
        return "late"
    return "early"
