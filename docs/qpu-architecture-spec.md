# QPU Architecture Specification

AstraQPU architecture specs describe a virtual QPU target. The first implementation accepts JSON. YAML is also supported when `PyYAML` is installed.

## Required Fields

```json
{
  "name": "tiny_3q_superconducting_mock",
  "clock": { "tick_ns": 10 },
  "qubits": {
    "q0": { "t1_us": 80, "t2_us": 60, "readout_error": 0.025 }
  },
  "topology": {
    "couplings": [["q0", "q1"]]
  },
  "native_gates": {
    "h": {
      "duration_ns": 40,
      "channels": ["drive:{q}"],
      "error": 0.001
    }
  },
  "calibration": {}
}
```

## Channel Templates

Gate channel requirements can include templates:

- `{q}` for one-qubit operations
- `{q0}` and `{q1}` for two-qubit operations

Examples:

```text
drive:{q}
readout:{q}
coupler:{q0}:{q1}
```

## Native Operations for v0

The v0 runtime expects these operations to exist in the architecture spec:

- `prep`
- one-qubit gates such as `h`, `x`, `sx`, `rz`
- two-qubit gates such as `cx`
- `measure`

