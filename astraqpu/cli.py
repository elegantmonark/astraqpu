from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

from astraqpu.arch import load_architecture
from astraqpu.backends import VirtualBackend
from astraqpu.errors import AstraQPUError
from astraqpu.frontend import parse_sutra_file
from astraqpu.scheduler import schedule_program


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="astraqpu")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate a QPU architecture spec")
    validate.add_argument("arch")

    compile_cmd = subparsers.add_parser("compile", help="compile a Sutra program into a scheduled stream")
    compile_cmd.add_argument("program")
    compile_cmd.add_argument("--arch", required=True)
    compile_cmd.add_argument("--out")

    run = subparsers.add_parser("run", help="run a Sutra program on a backend")
    run.add_argument("program")
    run.add_argument("--arch", required=True)
    run.add_argument("--backend", choices=("virtual", "serial"), default="virtual")
    run.add_argument("--out")

    args = parser.parse_args(argv)

    try:
        if args.command == "validate":
            arch = load_architecture(args.arch)
            print(json.dumps({"ok": True, "architecture": arch.name, "qubits": len(arch.qubits), "tick_ns": arch.tick_ns}, indent=2))
            return 0

        if args.command == "compile":
            scheduled = _compile(args.program, args.arch)
            _emit_json(scheduled.to_dict(), args.out)
            return 0

        if args.command == "run":
            scheduled = _compile(args.program, args.arch)
            if args.backend != "virtual":
                raise AstraQPUError("serial backend is planned for v0.2; use --backend virtual")
            trace = VirtualBackend().run(scheduled)
            _emit_json(trace.to_dict(), args.out)
            return 0
    except AstraQPUError as exc:
        print(f"astraqpu: error: {exc}", file=sys.stderr)
        return 2

    return 1


def _compile(program_path: str, arch_path: str):
    arch = load_architecture(arch_path)
    program = parse_sutra_file(program_path)
    return schedule_program(program, arch)


def _emit_json(data: dict, out: str | None) -> None:
    payload = json.dumps(data, indent=2)
    if out:
        path = Path(out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    raise SystemExit(main())

