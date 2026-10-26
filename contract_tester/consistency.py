"""Detect outputs whose *shape* changes between runs of the same prompt."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "object"


def signature(obj: Any) -> frozenset:
    """Set of (path, type) pairs describing the shape of a parsed output."""
    found: set[tuple[str, str]] = set()

    def walk(value: Any, path: str) -> None:
        found.add((path, _type_name(value)))
        if isinstance(value, dict):
            for key, sub in value.items():
                walk(sub, f"{path}.{key}")
        elif isinstance(value, list):
            for sub in value:
                walk(sub, f"{path}[]")

    walk(obj, "$")
    return frozenset(found)


def consistency_report(outputs: list[Any]) -> dict:
    """Compare parsed outputs produced for the same prompt."""
    n = len(outputs)
    if n < 2:
        return {"runs": n, "score": None, "unstable_paths": []}
    sigs = [signature(o) for o in outputs]
    _, modal_count = Counter(sigs).most_common(1)[0]
    types: dict[str, set[str]] = defaultdict(set)
    present: Counter = Counter()
    for sig in sigs:
        for path, type_name in sig:
            types[path].add(type_name)
        for path in {p for p, _ in sig}:
            present[path] += 1
    unstable = [
        {"path": p, "types": sorted(types[p]), "present_in": present[p]}
        for p in sorted(types)
        if present[p] < n or len(types[p]) > 1
    ]
    return {"runs": n, "score": modal_count / n, "unstable_paths": unstable}
