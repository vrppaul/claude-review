"""What a gate of ours that reads files reports: each place that breaks a rule, and the code it exits with."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

# What the process exits with
ALL_KEPT = 0
FAULT_FOUND = 1


class Fault(BaseModel):
    """One place that breaks a rule, and what is said of it."""

    model_config = ConfigDict(frozen=True)

    path: Path
    line: int
    says: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.says}"


def report(faults: list[Fault]) -> int:
    """Print each fault, and give the code the gate exits with."""
    for fault in faults:
        print(fault)
    return FAULT_FOUND if faults else ALL_KEPT
