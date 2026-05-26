from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Instruction:
    op: str
    qubits: tuple[str, ...] = ()
    bits: tuple[str, ...] = ()
    gate: str | None = None
    duration_ns: int | None = None
    name: str | None = None
    value: Any | None = None
    line: int = 0


@dataclass
class Program:
    declared_qubits: int | None = None
    declared_bits: int | None = None
    instructions: list[Instruction] = field(default_factory=list)

    def declared_qubit_names(self) -> set[str]:
        if self.declared_qubits is None:
            return set()
        return {f"q{i}" for i in range(self.declared_qubits)}

    def declared_bit_names(self) -> set[str]:
        if self.declared_bits is None:
            return set()
        return {f"c{i}" for i in range(self.declared_bits)}

