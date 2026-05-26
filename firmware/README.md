# Firmware

The first hardware-in-the-loop target will be an ESP32 or Arduino control unit using JSON Lines over serial.

Firmware responsibilities for v0.2:

- advertise device capabilities
- accept scheduled instruction packets
- emulate instruction timing
- expose calibration registers
- emit telemetry and fault flags
- return mock measurement results

