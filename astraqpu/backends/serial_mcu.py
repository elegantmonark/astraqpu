from __future__ import annotations

from astraqpu.errors import AstraQPUError


class SerialMCUBackend:
    name = "yantra.serial"

    def __init__(self, port: str, baudrate: int = 115200) -> None:
        self.port = port
        self.baudrate = baudrate

    def run(self, _program: object) -> None:
        raise AstraQPUError("serial MCU backend is reserved for v0.2; use --backend virtual in v0.1")

