"""Process data model used by the memory simulator."""

from dataclasses import dataclass


@dataclass
class Process:
    pid: int
    name: str
    start: int
    size: int

    def as_dict(self):
        return {
            "pid": self.pid,
            "name": self.name,
            "start": self.start,
            "size": self.size,
        }
