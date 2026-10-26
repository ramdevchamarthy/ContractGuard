"""Deterministic, model-free repair for *syntax* problems in model output.

This fixes the formatting mistakes models make most often (code fences,
chatty prefixes, trailing commas, Python-style literals). It never invents or
changes data, so it cannot hide schema violations such as a missing field.
"""
from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from typing import Any

_FENCE = re.compile(r"```[a-zA-Z]*\s*(.*?)```", re.S)
_TRAILING_COMMA = re.compile(r",(\s*[}\]])")


@dataclass
class RepairResult:
    ok: bool
    text: str
    steps: list[str] = field(default_factory=list)
    parsed: Any = None


def extract_balanced(text: str) -> str | None:
    """Return the first top-level {...} or [...] block (string-aware), or None."""
    start = next((i for i, ch in enumerate(text) if ch in "{["), None)
    if start is None:
        return None
    stack: list[str] = []
    in_str = False
    escaped = False
    quote = ""
    for j in range(start, len(text)):
        ch = text[j]
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                in_str = False
            continue
        if ch in "\"'":
            in_str, quote = True, ch
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if not stack or ch != stack[-1]:
                return None
            stack.pop()
            if not stack:
                return text[start : j + 1]
    return None  # never closed: truncated


def _try_json(text: str):
    try:
        return True, json.loads(text)
    except ValueError:
        return False, None


def _try_python_literal(text: str):
    try:
        value = ast.literal_eval(text)
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        return False, None
    return (True, value) if isinstance(value, (dict, list)) else (False, None)


def local_repair(raw: str | None) -> RepairResult:
    text = (raw or "").strip()
    steps: list[str] = []
    if not text:
        return RepairResult(False, "", ["nothing to repair"])

    fence = _FENCE.search(text)
    if fence:
        text = fence.group(1).strip()
        steps.append("removed markdown code fence")

    ok, value = _try_json(text)
    if ok:
        return RepairResult(True, text, steps, value)

    block = extract_balanced(text)
    if block is None:
        return RepairResult(False, text, steps + ["no complete JSON block found (output looks truncated)"])
    if block != text:
        text = block
        steps.append("extracted JSON from surrounding text")
        ok, value = _try_json(text)
        if ok:
            return RepairResult(True, text, steps, value)

    no_commas = _TRAILING_COMMA.sub(r"\1", text)
    if no_commas != text:
        text = no_commas
        steps.append("removed trailing comma")
        ok, value = _try_json(text)
        if ok:
            return RepairResult(True, text, steps, value)

    ok, value = _try_python_literal(text)
    if ok:
        text = json.dumps(value)
        steps.append("converted Python/single-quoted literal to JSON")
        return RepairResult(True, text, steps, value)

    return RepairResult(False, text, steps + ["could not repair syntax"])
