"""Memory manager that connects the simulator's separate algorithms."""

from .allocation import STRATEGIES, allocate_process, choose_hole
from .compaction import compact_processes
from .fragmentation import calculate_stats, find_holes
from .process import Process

MIN_TOTAL = 64
MAX_TOTAL = 4096

class MemoryManager:
    def __init__(self, total=512):
        self.reset(total)
        self.strategy = "first"

    def reset(self, total):
        if type(total) is not int or not MIN_TOTAL <= total <= MAX_TOTAL:
            raise ValueError(f"Total memory must be between {MIN_TOTAL} and {MAX_TOTAL} KB.")
        self.total = total
        self.processes = []
        self.next_pid = 1

    def set_strategy(self, strategy):
        if not isinstance(strategy, str) or strategy not in STRATEGIES:
            raise ValueError("Strategy must be first, best, or worst.")
        self.strategy = strategy

    def holes(self):
        return find_holes(self.processes, self.total)

    def choose_hole(self, requested_size):
        return choose_hole(self.holes(), self.strategy, requested_size)

    def stats(self):
        return calculate_stats(self.processes, self.total, self.holes())

    def snapshot(self, requested_size=None):
        stats = self.stats()
        preview = None
        if type(requested_size) is int and requested_size > 0:
            preview = self.choose_hole(requested_size)
        return {
            "total": self.total,
            "strategy": self.strategy,
            "processes": [process.as_dict() for process in self.processes],
            "holes": stats["holes"],
            "stats": {key: value for key, value in stats.items() if key != "holes"},
            "preview": preview,
        }

    def allocate(self, requested_size, name=""):
        outcome, self.next_pid = allocate_process(
            self.processes,
            self.total,
            self.strategy,
            self.next_pid,
            requested_size,
            name,
        )
        return outcome

    def free(self, pid):
        if type(pid) is not int:
            raise ValueError("Process ID must be an integer.")
        process = next((item for item in self.processes if item.pid == pid), None)
        if process is None:
            raise ValueError(f"Process {pid} does not exist.")
        self.processes.remove(process)
        return process.as_dict()

    def compact(self):
        return compact_processes(self.processes, self.total)

    def load_demo(self):
        self.processes = []
        self.next_pid = 1
        fractions = (0.12, 0.06, 0.16, 0.08, 0.14, 0.07, 0.12, 0.06)
        created = []
        cursor = 0
        for fraction in fractions:
            size = max(1, int(self.total * fraction + 0.5))
            process = Process(self.next_pid, f"P{self.next_pid}", cursor, size)
            self.next_pid += 1
            created.append(process)
            cursor += size
        self.processes = [process for index, process in enumerate(created) if index not in (1, 3, 5)]
        stats = self.stats()
        return {
            "finished": [created[index].name for index in (1, 3, 5)],
            "suggested_size": min(stats["free"], stats["largest"] + 1),
        }
