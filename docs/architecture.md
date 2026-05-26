# AstraQPU Architecture

AstraQPU models a quantum processor as a constrained hardware target rather than as a pure state-vector calculation problem.

The first runtime path is:

```text
Sutra instruction stream
  -> AstraQPU IR
  -> architecture validation
  -> physical scheduling
  -> runtime backend
  -> execution trace
```

## Host Runtime

The host runtime owns compilation, validation, scheduling, execution orchestration, and trace capture. It should eventually support multiple frontends, including a native low-level instruction format, OpenQASM subsets, and QML kernel wrappers.

## Architecture Model

An architecture spec defines:

- qubits and coherence metadata
- physical topology
- native operations
- operation durations
- readout latency
- control channel requirements
- calibration registers

This specification is the contract between compiler, scheduler, backend, and control unit.

## Scheduler

The scheduler assigns each instruction a start time while respecting:

- qubit availability
- control channel availability
- native gate support
- two-qubit coupling constraints
- explicit waits and barriers
- readout duration and latency

The scheduler is intentionally timing-first. A valid program is not only logically valid; it must also be executable on the declared architecture.

## Backends

The initial backend is **Akasha**, the virtual backend. It produces an execution trace from scheduled instructions.

The next backend is **Yantra Serial**, a microcontroller-backed control plane over serial. The MCU receives scheduled instructions, emulates execution timing, exposes calibration registers, emits telemetry, and returns measurement results.

