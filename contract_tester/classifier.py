"""Parse a model output and classify every way it breaks a JSON Schema contract.

Built on the open-source `jsonschema` library (Draft 2020-12). We do not
re-implement validation; we map its error keywords onto a small, stable
failure taxonomy that is useful to developers.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from jsonschema import Draft202012Validator

FAILURE_TYPES = (
    "invalid_json",
    "empty_output",
    "missing_field",
    "wrong_type",
    "invalid_enum",
    "extra_field",
    "constraint_violation",
    "request_error",
)

_KEYWORD_TO_TYPE = {
    "required": "missing_field",
    "type": "wrong_type",
    "enum": "invalid_enum",
    "const": "invalid_enum",
    "additionalProperties": "extra_field",
    "unevaluatedProperties": "extra_field",
}


@dataclass
class Violation:
    type: str
    path: str
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CheckResult:
    ok: bool
    parsed: Any = None
    violations: list[Violation] = field(default_factory=list)


def make_validator(schema: dict) -> Draft202012Validator:
    """Validate the schema itself first (raises jsonschema.SchemaError)."""
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _reject_constant(name: str):
    raise ValueError(f"non-standard JSON constant {name!r} is not allowed")


def diagnose_invalid_json(raw: str) -> list[str]:
    """Best-effort hints about why a string is not JSON."""
    s = raw.strip()
    hints: list[str] = []
    if s.startswith("```"):
        hints.append("wrapped in a markdown code fence")
    elif s and s[0] not in "{[":
        hints.append("text before the JSON")
    if re.search(r",\s*[}\]]", s):
        hints.append("trailing comma")
    if re.search(r"(?<![\w\"])'[^']*'\s*:", s):
        hints.append("single-quoted keys")
    if s and s[-1] not in "}]" and not s.endswith("```"):
        hints.append("ends unexpectedly (truncated or trailing text)")
    return hints


def parse_strict(raw: str | None) -> tuple[Any, Violation | None]:
    if raw is None or not raw.strip():
        return None, Violation("empty_output", "$", "the model returned no text")
    try:
        return json.loads(raw, parse_constant=_reject_constant), None
    except ValueError as exc:  # JSONDecodeError is a ValueError
        message = str(exc)
        hints = diagnose_invalid_json(raw)
        if hints:
            message += " (likely cause: " + "; ".join(hints) + ")"
        return None, Violation("invalid_json", "$", message)


def _path(parts) -> str:
    out = "$"
    for part in parts:
        out += f"[{part}]" if isinstance(part, int) else f".{part}"
    return out


def classify_error(err) -> list[Violation]:
    """Turn one jsonschema error into one or more Violations."""
    base = _path(err.absolute_path)
    keyword = err.validator
    if keyword == "required":
        match = re.match(r"'(.*)' is a required property", err.message)
        name = match.group(1) if match else "?"
        return [Violation("missing_field", f"{base}.{name}", err.message)]
    if keyword in ("additionalProperties", "unevaluatedProperties"):
        names = re.findall(r"'([^']+)'", err.message) or ["?"]
        return [
            Violation("extra_field", f"{base}.{n}", f"unexpected field {n!r} (schema forbids extra fields)")
            for n in names
        ]
    kind = _KEYWORD_TO_TYPE.get(keyword, "constraint_violation")
    return [Violation(kind, base, err.message)]


def validate_instance(obj: Any, validator: Draft202012Validator) -> list[Violation]:
    errors = sorted(validator.iter_errors(obj), key=lambda e: [str(p) for p in e.absolute_path])
    violations: list[Violation] = []
    for err in errors:
        violations.extend(classify_error(err))
    return violations


def check_output(raw: str | None, validator: Draft202012Validator) -> CheckResult:
    """Strictly parse `raw` and validate it. Never raises on bad model output."""
    parsed, problem = parse_strict(raw)
    if problem is not None:
        return CheckResult(ok=False, parsed=None, violations=[problem])
    violations = validate_instance(parsed, validator)
    return CheckResult(ok=not violations, parsed=parsed, violations=violations)
