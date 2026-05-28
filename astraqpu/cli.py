from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

from astraqpu.arch import load_architecture
from astraqpu.backends import SerialMCUBackend, VirtualBackend
from astraqpu.errors import AstraQPUError
from astraqpu.frontend import parse_sutra_file
from astraqpu.protocol import SerialProtocol
from astraqpu.runtime.compare import compare_traces, load_trace
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
    run.add_argument("--port", help="serial port for --backend serial, for example COM5 or /dev/ttyUSB0")
    run.add_argument("--baudrate", type=int, default=115200)
    run.add_argument("--timeout", type=float, default=10.0)
    run.add_argument("--job-id", default="job_001")
    run.add_argument("--out")

    serial_dump = subparsers.add_parser("serial-dump", help="print JSON Lines that would be sent to a control unit")
    serial_dump.add_argument("program")
    serial_dump.add_argument("--arch", required=True)
    serial_dump.add_argument("--job-id", default="job_001")

    trace_compare = subparsers.add_parser("trace-compare", help="compare expected and observed execution traces")
    trace_compare.add_argument("--expected", help="expected astraqpu.trace.v0 JSON file")
    trace_compare.add_argument("--observed", help="observed astraqpu.trace.v0 JSON file")
    trace_compare.add_argument("--program", help="program to compile into an expected virtual trace")
    trace_compare.add_argument("--arch", help="architecture spec for --program")
    trace_compare.add_argument("--backend", choices=("file", "serial"), default="file")
    trace_compare.add_argument("--port", help="serial port for --backend serial")
    trace_compare.add_argument("--baudrate", type=int, default=115200)
    trace_compare.add_argument("--timeout", type=float, default=10.0)
    trace_compare.add_argument("--job-id", default="job_001")
    trace_compare.add_argument("--tolerance-ns", type=int, default=0)
    trace_compare.add_argument("--out")

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
            if args.backend == "virtual":
                trace = VirtualBackend().run(scheduled)
            else:
                if not args.port:
                    raise AstraQPUError("--backend serial requires --port")
                trace = SerialMCUBackend(
                    port=args.port,
                    baudrate=args.baudrate,
                    timeout_s=args.timeout,
                    job_id=args.job_id,
                ).run(scheduled)
            _emit_json(trace.to_dict(), args.out)
            return 0

        if args.command == "serial-dump":
            scheduled = _compile(args.program, args.arch)
            for line in SerialProtocol(job_id=args.job_id).host_lines(scheduled):
                print(line.decode("utf-8"), end="")
            return 0

        if args.command == "trace-compare":
            expected, observed = _trace_pair(args)
            report = compare_traces(expected, observed, tolerance_ns=args.tolerance_ns)
            _emit_json(report.to_dict(), args.out)
            return 0
    except AstraQPUError as exc:
        print(f"astraqpu: error: {exc}", file=sys.stderr)
        return 2

    return 1


def _compile(program_path: str, arch_path: str):
    arch = load_architecture(arch_path)
    program = parse_sutra_file(program_path)
    return schedule_program(program, arch)


def _trace_pair(args):
    if args.expected and args.observed:
        return load_trace(args.expected), load_trace(args.observed)

    if not args.program or not args.arch:
        raise AstraQPUError("trace-compare requires either --expected and --observed, or --program and --arch")

    scheduled = _compile(args.program, args.arch)
    expected = VirtualBackend().run(scheduled)

    if args.backend == "file":
        if not args.observed:
            raise AstraQPUError("trace-compare --backend file requires --observed")
        observed = load_trace(args.observed)
        return expected, observed

    if not args.port:
        raise AstraQPUError("trace-compare --backend serial requires --port")
    observed = SerialMCUBackend(
        port=args.port,
        baudrate=args.baudrate,
        timeout_s=args.timeout,
        job_id=args.job_id,
    ).run(scheduled)
    return expected, observed


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
