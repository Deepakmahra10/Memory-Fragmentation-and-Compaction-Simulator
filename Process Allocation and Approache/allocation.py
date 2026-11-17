"""Memory placement strategies and process allocation."""

from .fragmentation import calculate_stats, find_holes
from .process import Process


STRATEGIES = {"first", "best", "worst"}


def choose_hole(holes, strategy, requested_size):
    candidates = [hole for hole in holes if hole["size"] >= requested_size]
    if not candidates:
        return None
    if strategy == "best":
        return min(candidates, key=lambda hole: (hole["size"], hole["start"]))
    if strategy == "worst":
        return min(candidates, key=lambda hole: (-hole["size"], hole["start"]))
    return candidates[0]


def allocate_process(processes, total, strategy, next_pid, requested_size, name):
    if type(requested_size) is not int or not 1 <= requested_size <= total:
        raise ValueError(f"Process size must be a whole number from 1 to {total} KB.")

    holes = find_holes(processes, total)
    hole = choose_hole(holes, strategy, requested_size)
    if hole is None:
        stats = calculate_stats(processes, total, holes)
        result = "fragmented" if stats["free"] >= requested_size else "out_of_memory"
        return {"result": result, "stats": stats}, next_pid

    process_name = str(name).strip()[:10] or f"P{next_pid}"
    process = Process(next_pid, process_name, hole["start"], requested_size)
    processes.append(process)
    return {
        "result": "allocated",
        "process": process.as_dict(),
        "hole": hole,
    }, next_pid + 1
