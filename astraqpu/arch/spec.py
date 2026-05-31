from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

from astraqpu.errors import ArchitectureError


@dataclass(frozen=True)
class OperationSpec:
    name: str
    duration_ns: int
    channels: tuple[str, ...]
    latency_ns: int = 0
    virtual: bool = False
    error: float | None = None


@dataclass(frozen=True)
class ArchitectureSpec:
    name: str
    tick_ns: int
    qubits: dict[str, dict[str, Any]]
    couplings: frozenset[frozenset[str]]
    native_gates: dict[str, OperationSpec]
    calibration: dict[str, Any]

    def require_qubits(self, qubits: tuple[str, ...]) -> None:
        missing = [qubit for qubit in qubits if qubit not in self.qubits]
        if missing:
            raise ArchitectureError(f"architecture {self.name!r} does not define qubits: {', '.join(missing)}")

    def require_operation(self, name: str) -> OperationSpec:
        op = self.native_gates.get(name.lower())
        if op is None:
            raise ArchitectureError(f"architecture {self.name!r} does not support native operation {name!r}")
        return op

    def supports_coupling(self, q0: str, q1: str) -> bool:
        return frozenset((q0, q1)) in self.couplings

    def resolve_channels(self, operation: OperationSpec, qubits: tuple[str, ...]) -> tuple[str, ...]:
        values = {}
        if qubits:
            values["q"] = qubits[0]
            values["q0"] = qubits[0]
        if len(qubits) > 1:
            values["q1"] = qubits[1]
        return tuple(template.format(**values) for template in operation.channels)


def load_architecture(path: str | Path) -> ArchitectureSpec:
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        data = _load_yaml(raw, path)
    else:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ArchitectureError(f"{path}: invalid JSON architecture spec") from exc
    return architecture_from_dict(data)


def architecture_from_dict(data: dict[str, Any]) -> ArchitectureSpec:
    try:
        name = str(data["name"])
        tick_ns = int(data["clock"]["tick_ns"])
        qubits = dict(data["qubits"])
        couplings = frozenset(frozenset(edge) for edge in data.get("topology", {}).get("couplings", []))
        native_gates = {
            gate_name.lower(): OperationSpec(
                name=gate_name.lower(),
                duration_ns=int(spec.get("duration_ns", 0)),
                latency_ns=int(spec.get("latency_ns", spec.get("latency", 0))),
                channels=tuple(spec.get("channels", ())),
                virtual=bool(spec.get("virtual", False)),
                error=spec.get("error"),
            )
            for gate_name, spec in data["native_gates"].items()
        }
        calibration = dict(data.get("calibration", {}))
    except KeyError as exc:
        raise ArchitectureError(f"missing required architecture field: {exc.args[0]}") from exc

    if tick_ns <= 0:
        raise ArchitectureError("clock.tick_ns must be positive")
    for edge in couplings:
        if len(edge) != 2:
            raise ArchitectureError("topology couplings must contain exactly two qubits")
        missing = [qubit for qubit in edge if qubit not in qubits]
        if missing:
            raise ArchitectureError(f"topology references unknown qubits: {', '.join(missing)}")
    for required in ("prep", "measure"):
        if required not in native_gates:
            raise ArchitectureError(f"architecture must define native operation {required!r}")

    return ArchitectureSpec(
        name=name,
        tick_ns=tick_ns,
        qubits=qubits,
        couplings=couplings,
        native_gates=native_gates,
        calibration=calibration,
    )


def _load_yaml(raw: str, path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise ArchitectureError(f"{path}: YAML specs require PyYAML; use JSON or install astraqpu[yaml]") from exc
    return yaml.safe_load(raw)
