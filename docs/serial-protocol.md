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

The serial backend requires `pyserial`:

```bash
python -m pip install pyserial
```

## Future Binary Frame

```text
MAGIC | VERSION | TYPE | LENGTH | PAYLOAD | CRC32
```
