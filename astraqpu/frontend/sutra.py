from __future__ import annotations

from pathlib import Path
import re

from astraqpu.errors import ParseError
from astraqpu.ir import Instruction, Program

_DURATION_RE = re.compile(r"^(?P<value>\d+)(?P<unit>ns|us|ms)$", re.IGNORECASE)


def parse_sutra_file(path: str | Path) -> Program:
    return parse_sutra(Path(path).read_text(encoding="utf-8"), source=str(path))


def parse_sutra(text: str, source: str = "<memory>") -> Program:
    program = Program()

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue

        parts = line.split()
        keyword = parts[0].upper()

        try:
            if keyword == "DECLARE_QUBITS":
                _expect_len(parts, 2, line_no, source)
                program.declared_qubits = _parse_count(parts[1], line_no, source)
            elif keyword == "DECLARE_BITS":
                _expect_len(parts, 2, line_no, source)
                program.declared_bits = _parse_count(parts[1], line_no, source)
            elif keyword == "PREP":
                _expect_len(parts, 2, line_no, source)
                program.instructions.append(Instruction("prep", qubits=(_qubit(parts[1], line_no, source),), line=line_no))
            elif keyword == "GATE":
                if len(parts) < 3:
                    raise ParseError(f"{source}:{line_no}: GATE requires a gate name and at least one qubit")
                gate = parts[1].lower()
                qubits = tuple(_qubit(token, line_no, source) for token in parts[2:])
                program.instructions.append(Instruction("gate", gate=gate, qubits=qubits, line=line_no))
            elif keyword == "MEASURE":
                if len(parts) != 4 or parts[2] != "->":
                    raise ParseError(f"{source}:{line_no}: MEASURE syntax is MEASURE qN -> cN")
                program.instructions.append(
                    Instruction(
                        "measure",
                        qubits=(_qubit(parts[1], line_no, source),),
                        bits=(_bit(parts[3], line_no, source),),
                        line=line_no,
                    )
                )
            elif keyword == "WAIT":
                _expect_len(parts, 2, line_no, source)
                program.instructions.append(Instruction("wait", duration_ns=_duration(parts[1], line_no, source), line=line_no))
            elif keyword == "BARRIER":
                if len(parts) < 2:
                    raise ParseError(f"{source}:{line_no}: BARRIER requires at least one qubit")
                qubits = tuple(_qubit(token, line_no, source) for token in parts[1:])
                program.instructions.append(Instruction("barrier", qubits=qubits, line=line_no))
            elif keyword == "SET_REG":
                if len(parts) < 3:
                    raise ParseError(f"{source}:{line_no}: SET_REG requires a register name and value")
                program.instructions.append(Instruction("set_reg", name=_register(parts[1], line_no, source), value=" ".join(parts[2:]), line=line_no))
            elif keyword == "END":
                _expect_len(parts, 1, line_no, source)
                break
            else:
                raise ParseError(f"{source}:{line_no}: unknown instruction {parts[0]!r}")
        except ValueError as exc:
            raise ParseError(f"{source}:{line_no}: {exc}") from exc

    _validate_declarations(program, source)
    return program


def _validate_declarations(program: Program, source: str) -> None:
    if program.declared_qubits is None:
        raise ParseError(f"{source}: missing DECLARE_QUBITS")
    if program.declared_bits is None:
        raise ParseError(f"{source}: missing DECLARE_BITS")

    declared_qubits = program.declared_qubit_names()
    declared_bits = program.declared_bit_names()

    for instr in program.instructions:
        for qubit in instr.qubits:
            if qubit not in declared_qubits:
                raise ParseError(f"{source}:{instr.line}: undeclared qubit {qubit}")
        for bit in instr.bits:
            if bit not in declared_bits:
                raise ParseError(f"{source}:{instr.line}: undeclared bit {bit}")


def _expect_len(parts: list[str], length: int, line_no: int, source: str) -> None:
    if len(parts) != length:
        raise ParseError(f"{source}:{line_no}: expected {length} fields, found {len(parts)}")


def _parse_count(token: str, line_no: int, source: str) -> int:
    value = int(token)
    if value < 0:
        raise ParseError(f"{source}:{line_no}: declaration count must be non-negative")
    return value


def _duration(token: str, line_no: int, source: str) -> int:
    match = _DURATION_RE.match(token)
    if not match:
        raise ParseError(f"{source}:{line_no}: duration must use ns, us, or ms")
    value = int(match.group("value"))
    unit = match.group("unit").lower()
    scale = {"ns": 1, "us": 1_000, "ms": 1_000_000}[unit]
    return value * scale


def _qubit(token: str, line_no: int, source: str) -> str:
    if not re.match(r"^q\d+$", token):
        raise ParseError(f"{source}:{line_no}: invalid qubit name {token!r}")
    return token


def _bit(token: str, line_no: int, source: str) -> str:
    if not re.match(r"^c\d+$", token):
        raise ParseError(f"{source}:{line_no}: invalid bit name {token!r}")
    return token


def _register(token: str, line_no: int, source: str) -> str:
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_.:]*$", token):
        raise ParseError(f"{source}:{line_no}: invalid register name {token!r}")
    return token
