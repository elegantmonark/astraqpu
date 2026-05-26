# Serial Protocol

The first hardware-in-the-loop backend will use JSON Lines over serial. This keeps the control plane easy to inspect and debug before moving to binary framing.

## Host to MCU

```json
{"type":"HELLO","proto":"astraqpu.serial.v0"}
{"type":"LOAD","job_id":"bell_001","instruction_count":4}
{"type":"INST","job_id":"bell_001","id":1,"t_ns":0,"op":"gate","gate":"h","qubits":["q0"],"duration_ns":40}
{"type":"RUN","job_id":"bell_001"}
```

## MCU to Host

```json
{"type":"HELLO","proto":"astraqpu.serial.v0","device":"esp32","tick_ns":10}
{"type":"ACK","job_id":"bell_001"}
{"type":"EVT","job_id":"bell_001","t_us":1020,"event":"instruction_start","id":1}
{"type":"EVT","job_id":"bell_001","t_us":1060,"event":"instruction_end","id":1}
{"type":"RESULT","job_id":"bell_001","bits":{"c0":1,"c1":1}}
```

## Future Binary Frame

```text
MAGIC | VERSION | TYPE | LENGTH | PAYLOAD | CRC32
```

