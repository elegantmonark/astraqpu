from __future__ import annotations

from astraqpu.errors import AstraQPUError
from astraqpu.protocol import SerialProtocol
from astraqpu.protocol.serial_jsonl import SerialSession
from astraqpu.scheduler import ScheduledProgram


class SerialMCUBackend:
    name = "yantra.serial"

    def __init__(self, port: str, baudrate: int = 115200, timeout_s: float = 10.0, job_id: str = "job_001") -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout_s = timeout_s
        self.job_id = job_id

    def run(self, program: ScheduledProgram):
        try:
            import serial
        except ImportError as exc:
            raise AstraQPUError("serial backend requires pyserial; install with `python -m pip install pyserial`") from exc

        try:
            with serial.Serial(self.port, self.baudrate, timeout=0.25) as transport:
                session = SerialSession(
                    transport=transport,
                    protocol=SerialProtocol(job_id=self.job_id),
                    timeout_s=self.timeout_s,
                    inter_write_delay_s=0.01,
                )
                return session.run(program)
        except OSError as exc:
            raise AstraQPUError(f"could not open serial port {self.port!r}: {exc}") from exc
