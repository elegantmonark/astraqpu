"""Domain errors raised by AstraQPU components."""


class AstraQPUError(Exception):
    """Base exception for AstraQPU runtime failures."""


class ArchitectureError(AstraQPUError):
    """Raised when a QPU architecture spec is invalid."""


class ParseError(AstraQPUError):
    """Raised when a Sutra instruction stream cannot be parsed."""


class ScheduleError(AstraQPUError):
    """Raised when a program cannot be scheduled for an architecture."""

