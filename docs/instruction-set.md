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

