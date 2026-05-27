# ESP32 Control Unit

This directory is reserved for the v0.2 Yantra serial control unit.

The initial firmware should implement the JSON Lines protocol in `docs/serial-protocol.md`.

Recommended ESP32 implementation shape:

- one serial RX task that parses JSON Lines
- one runtime task that executes the scheduled instruction queue
- one telemetry task that emits periodic `TELEM` messages
- a small register table for calibration and fault flags
- a fixed instruction buffer for `LOAD` and `INST` messages

The Arduino sketch in `firmware/arduino/astraqpu_control_unit` is intentionally dependency-free and can be used as the first protocol reference.
