# AstraQPU

A virtual QPU runtime for architecture aware scheduling, control, and hardware in the loop execution.

AstraQPU prototypes the software architecture around how a quantum processor could be controlled, scheduled, debugged, and virtualized. The project focuses on runtime architecture, native instruction scheduling, hardware constraints, control plane interaction, execution traces, and telemetry rather than generic circuit simulation.

## Project Shape

AstraQPU is organized around a host runtime and a physical mock control unit:

```text
program input -> IR -> architecture model -> scheduler -> runtime backend -> trace
                                                             |
                                                             +-> virtual backend
                                                             +-> serial MCU backend
```

The initial backend is virtual. The next backend is an Arduino/ESP32 control unit that accepts scheduled instructions over serial and emulates timing triggers, calibration registers, measurement latency, fault flags, and telemetry.

## Naming System

- **AstraQPU**: project and runtime
- **Sutra**: instruction stream / IR
- **Yantra**: hardware abstraction layer
- **Niyantra**: scheduler and control runtime
- **Akasha**: virtual backend
- **Tejas**: telemetry engine

## Quick Start

From this repository:

```bash
python -m astraqpu.cli validate examples/arch/tiny_3q.json
python -m astraqpu.cli compile examples/bell.aqis --arch examples/arch/tiny_3q.json --out build/bell.scheduled.json
python -m astraqpu.cli run examples/bell.aqis --arch examples/arch/tiny_3q.json --backend virtual
python -m astraqpu.cli serial-dump examples/bell.aqis --arch examples/arch/tiny_3q.json --job-id bell_001
python -m astraqpu.cli serial-dump examples/calibration_pulse.aqis --arch examples/arch/tiny_3q.json --job-id cal_001
python -m astraqpu.cli trace-compare --expected expected.json --observed observed.json --tolerance-ns 1000 --allow-mismatch
```

## MVP Scope

The first milestone proves that AstraQPU can:

- load a virtual QPU architecture specification
- parse a small low-level QPU instruction stream
- validate native gates and topology constraints
- schedule instructions under qubit/channel timing constraints
- emit a machine-readable execution trace
- prepare the same scheduled stream for a future serial MCU backend
- emit JSON Lines control plane traffic for an Arduino or ESP32 control unit
- carry calibration register writes through the scheduled instruction stream
- compare expected runtime traces against observed control unit traces

## Status

Early architecture/runtime foundation. The current focus is a narrow but real execution path: QPU architecture spec -> instruction parser -> scheduler -> virtual execution trace.

## Security

Security policy and project guardrails are in [SECURITY.md](SECURITY.md) and [docs/security.md](docs/security.md).

## Citation

If AstraQPU helps your work, please cite it:

```text
Trishan Biswas. AstraQPU: A virtual QPU runtime for architecture aware scheduling, control, and hardware in the loop execution. 2026. https://github.com/elegantmonark/astraqpu
```

## License

Apache License 2.0.

Copyright 2026 Trishan Biswas / elegantmonark.
