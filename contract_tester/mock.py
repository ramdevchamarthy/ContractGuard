"""A seeded, offline stand-in for an LLM that breaks its JSON contract on purpose.

It lets the app, the tests and the CI gate run with no model and no network.
Results from it are SIMULATED and must never be presented as real model benchmarks.
"""
from __future__ import annotations

import json
import random
from typing import Any

PROFILES = {"sloppy": 0.60, "careful": 0.15}


def example_from_schema(schema: dict, rng: random.Random) -> Any:
    """Build a plausible instance from a (simple) JSON Schema."""
    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        return rng.choice(schema["enum"])
    kind = schema.get("type")
    if isinstance(kind, list):
        non_null = [k for k in kind if k != "null"]
        kind = non_null[0] if non_null else "null"
    if kind == "object" or (kind is None and "properties" in schema):
        required = set(schema.get("required", []))
        out = {}
        for key, sub in schema.get("properties", {}).items():
            if key in required or rng.random() < 0.5:
                out[key] = example_from_schema(sub, rng)
        return out
    if kind == "array":
        low = schema.get("minItems", 0)
        high = schema.get("maxItems", 3)
        count = min(max(low, 2), high)
        return [example_from_schema(schema.get("items", {}), rng) for _ in range(count)]
    if kind == "string":
        text = "sample text"
        return text.ljust(schema.get("minLength", 0), "x")
    if kind == "integer":
        low = int(schema.get("minimum", 0))
        high = int(schema.get("maximum", low + 100))
        return rng.randint(low, high)
    if kind == "number":
        low = float(schema.get("minimum", 0))
        high = float(schema.get("maximum", low + 1))
        return round(rng.uniform(low, high), 2)
    if kind == "boolean":
        return rng.choice([True, False])
    if kind == "null":
        return None
    return "sample"


def _fenced(obj, schema, rng):
    return "```json\n" + json.dumps(obj, indent=2) + "\n```"


def _prose(obj, schema, rng):
    return "Sure! Here is the JSON you asked for:\n" + json.dumps(obj)


def _trailing_comma(obj, schema, rng):
    if not isinstance(obj, dict):
        return None
    return json.dumps(obj, indent=2).rstrip()[:-1].rstrip() + ",\n}"


def _single_quotes(obj, schema, rng):
    return repr(obj)


def _truncated(obj, schema, rng):
    text = json.dumps(obj)
    return text[: max(2, int(len(text) * 0.7))]


def _missing_field(obj, schema, rng):
    keys = [k for k in schema.get("required", []) if isinstance(obj, dict) and k in obj]
    if not keys:
        return None
    broken = dict(obj)
    del broken[rng.choice(keys)]
    return json.dumps(broken)


def _wrong_type(obj, schema, rng):
    if not isinstance(obj, dict):
        return None
    props = schema.get("properties", {})
    for key, value in obj.items():
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return json.dumps({**obj, key: str(value)})
        if isinstance(value, str) and "enum" not in props.get(key, {}):
            return json.dumps({**obj, key: 42})
    return None


def _bad_enum(obj, schema, rng):
    if not isinstance(obj, dict):
        return None
    for key, sub in schema.get("properties", {}).items():
        if "enum" in sub and key in obj:
            return json.dumps({**obj, key: "unknown"})
    return None


def _extra_field(obj, schema, rng):
    if not isinstance(obj, dict):
        return None
    return json.dumps({**obj, "notes": "added by the model"})


_CORRUPTIONS = [
    (_fenced, 2), (_prose, 2), (_trailing_comma, 1), (_single_quotes, 1), (_truncated, 1),
    (_missing_field, 2), (_wrong_type, 2), (_bad_enum, 1), (_extra_field, 1),
]


class MockClient:
    """Deterministic fake model. `model` is a profile name: sloppy or careful."""

    def __init__(self, schema: dict, model: str = "sloppy", seed: int = 7):
        self.schema = schema
        self.name = f"mock-{model}"
        self.error_rate = PROFILES.get(model, 0.40)
        self.seed = seed
        self.calls = 0
        self._last_clean: Any = None

    def complete(self, prompt, system=None, temperature=0.7, schema=None,
                 structured="none", purpose="generate") -> str:
        self.calls += 1
        rng = random.Random(f"{self.seed}:{self.calls}")
        if purpose == "repair":
            if self._last_clean is not None and rng.random() < 0.8:
                return json.dumps(self._last_clean)
            return "Here you go: " + json.dumps(self._last_clean)
        obj = example_from_schema(self.schema, rng)
        self._last_clean = obj
        if structured == "json_schema":
            return json.dumps(obj)  # constrained decoding never breaks the contract
        rate = self.error_rate * (0.6 if structured == "json_object" else 1.0)
        if rng.random() >= rate:
            return json.dumps(obj)
        funcs, weights = zip(*_CORRUPTIONS)
        for _ in range(5):
            out = rng.choices(funcs, weights)[0](obj, self.schema, rng)
            if out is not None:
                return out
        return _prose(obj, self.schema, rng)
