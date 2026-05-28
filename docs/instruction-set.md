# Sutra Instruction Stream

Sutra is AstraQPU's low-level instruction stream. It is deliberately small in v0 so the runtime can focus on timing, scheduling, architecture constraints, and backend execution.

## Example

```text
DECLARE_QUBITS 2
DECLARE_BITS 2

PREP q0
PREP q1
GATE H q0
GATE CX q0 q1
MEASURE q0 -> c0
MEASURE q1 -> c1
END
```

## v0 Instructions

```text
DECLARE_QUBITS n
DECLARE_BITS n
PREP q
GATE name q...
MEASURE q -> c
WAIT duration
BARRIER q...
SET_REG name value
END
```

Durations accept `ns`, `us`, or `ms`.

## Register Writes

`SET_REG` writes a control register into the scheduled stream. It is meant for values the control plane should see, such as drive amplitudes, readout settings, timing knobs, or fault flags.

```text
SET_REG q0.drive_amp 0.42
SET_REG q1.drive_amp 0.39
SET_REG readout.latency_scale 1.00
```

The serial backend sends these as normal instructions with `op` set to `set_reg`, plus a `register` and `value` field.

## Scheduled Form

The compiler lowers Sutra into a scheduled JSON stream:

```json
{
  "format": "astraqpu.scheduled.v0",
  "instructions": [
    {
      "id": 1,
      "t_ns": 0,
      "op": "gate",
      "gate": "h",
      "qubits": ["q0"],
      "duration_ns": 40,
      "channels": ["drive:q0"]
    }
  ]
}
```
