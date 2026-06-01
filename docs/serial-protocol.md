# Serial Protocol

The first hardware-in-the-loop backend will use JSON Lines over serial. This keeps the control plane easy to inspect and debug before moving to binary framing.

## Host to MCU

```json
{"type":"HELLO","proto":"astraqpu.serial.v0"}
{"type":"LOAD","proto":"astraqpu.serial.v0","job_id":"bell_001","architecture":"tiny_3q_superconducting_mock","tick_ns":10,"instruction_count":4}
{"type":"INST","proto":"astraqpu.serial.v0","job_id":"bell_001","id":1,"t_ns":0,"op":"gate","gate":"h","qubits":["q0"],"duration_ns":40,"latency_ns":0,"channels":["drive:q0"]}
{"type":"INST","proto":"astraqpu.serial.v0","job_id":"bell_001","id":2,"t_ns":0,"op":"set_reg","register":"q0.drive_amp","value":"0.42","duration_ns":0,"latency_ns":0}
{"type":"RUN","job_id":"bell_001"}
```

## MCU to Host

```json
{"type":"HELLO","proto":"astraqpu.serial.v0","device":"esp32","tick_ns":10}
{"type":"ACK","job_id":"bell_001"}
{"type":"EVT","job_id":"bell_001","t_us":1020,"event":"instruction_start","id":1}
{"type":"EVT","job_id":"bell_001","t_us":1060,"event":"instruction_end","id":1}
{"type":"EVT","job_id":"bell_001","event":"register_set","id":2,"op":"set_reg","register":"q0.drive_amp","value":"0.42","t_ns":0}
{"type":"RESULT","job_id":"bell_001","bits":{"c0":1,"c1":1}}
```

## Host CLI

Print the exact JSON Lines stream without opening a serial port:

```bash
python -m astraqpu.cli serial-dump examples/bell.aqis --arch examples/arch/tiny_3q.json --job-id bell_001
```

Run against a board:

```bash
python -m astraqpu.cli run examples/bell.aqis --arch examples/arch/tiny_3q.json --backend serial --port COM5
```

Compare the board reported trace against the expected runtime trace:

```bash
python -m astraqpu.cli trace-compare --program examples/bell.aqis --arch examples/arch/tiny_3q.json --backend serial --port COM5 --tolerance-ns 1000
```

By default, `trace-compare` returns a non zero exit code when traces do not match. Use `--allow-mismatch` when you only want the JSON report.

For a readable terminal summary:

```bash
python -m astraqpu.cli trace-compare --expected expected.json --observed observed.json --format summary --allow-mismatch
```

The serial backend requires `pyserial`:

```bash
python -m pip install pyserial
```

## Protocol Limits

The host runtime keeps the first protocol limits small on purpose:

```text
max JSON line size: 4096 bytes
max instructions per job: 256
max job id length: 48 characters
max register name length: 48 characters
max register value length: 96 characters
max trace events collected from a device: 4096
```

These limits are there so a bad serial line or broken board firmware cannot make the host accept unbounded input.

Device messages are schema checked before they become trace events. For example, `EVT` must include `job_id`, `event`, `id`, `op`, and either `t_ns` or `t_us`. `RESULT` must include a `bits` object.

The host also validates outgoing serial jobs before writing to the transport. Oversized jobs, oversized job ids, oversized register names, and oversized register values are rejected before any line is sent.

The Arduino reference firmware has smaller board side limits because it is intentionally dependency free and memory light:

```text
max serial line length: 512 characters
max loaded instructions: 64
max stored registers: 24
max board job id length: 31 characters
max board register name length: 31 characters
max board register value length: 31 characters
```

When the firmware rejects a command it sends `NACK` with a specific reason, for example `missing_job_id`, `instruction_buffer_full`, `unknown_op`, or `register_value_too_long`.

## Future Binary Frame

```text
MAGIC | VERSION | TYPE | LENGTH | PAYLOAD | CRC32
```
