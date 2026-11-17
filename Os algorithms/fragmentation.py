"""Free-hole detection and external fragmentation statistics."""


def find_holes(processes, total):
    holes = []
    cursor = 0
    for process in sorted(processes, key=lambda item: item.start):
        if process.start > cursor:
            holes.append({"start": cursor, "size": process.start - cursor})
        cursor = process.start + process.size
    if cursor < total:
        holes.append({"start": cursor, "size": total - cursor})
    return holes


def calculate_stats(processes, total, holes=None):
    if holes is None:
        holes = find_holes(processes, total)
    used = sum(process.size for process in processes)
    free = total - used
    largest = max((hole["size"] for hole in holes), default=0)
    fragmentation = (1 - largest / free) * 100 if free else 0
    return {
        "used": used,
        "free": free,
        "largest": largest,
        "frag": fragmentation,
        "holes": holes,
    }
