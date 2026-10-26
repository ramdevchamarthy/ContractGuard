"""Run a schema contract against a model many times and collect evidence."""
from __future__ import annotations

import math
import time
from collections import Counter, defaultdict
from typing import Any

import requests

from .classifier import check_output, make_validator
from .consistency import consistency_report
from .repair import local_repair

MAX_RAW_CHARS = 4000


def build_system_prompt(schema: dict) -> str:
    import json
    return (
        "Respond with a single JSON value that conforms to this JSON Schema. "
        "Output JSON only, with no commentary.\n" + json.dumps(schema)
    )


def build_repair_prompt(raw: str, violations) -> str:
    issues = "\n".join(f"- {v.path}: {v.message}" for v in violations[:10])
    return (
        "Your previous output broke the JSON contract.\n"
        f"Problems:\n{issues}\n\nPrevious output:\n{(raw or '')[:MAX_RAW_CHARS]}\n\n"
        "Return only the corrected JSON."
    )


class OpenAICompatClient:
    """Any OpenAI-compatible /chat/completions endpoint (Ollama, vLLM, llama.cpp, LM Studio...)."""

    def __init__(self, base_url: str, model: str, api_key: str | None = None, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.name = model

    def complete(self, prompt, system=None, temperature=0.7, schema=None,
                 structured="none", purpose="generate") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body: dict[str, Any] = {"model": self.model, "messages": messages, "temperature": temperature}
        if structured == "json_object":
            body["response_format"] = {"type": "json_object"}
        elif structured == "json_schema" and schema:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "contract", "schema": schema, "strict": True},
            }
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        resp = requests.post(f"{self.base_url}/chat/completions", json=body,
                             headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"] or ""


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float] | None:
    """95% Wilson score interval for a pass rate (honest with small samples)."""
    if total <= 0:
        return None
    p = successes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def _clip(text: str) -> str:
    return text if len(text) <= MAX_RAW_CHARS else text[:MAX_RAW_CHARS] + "\n...[truncated]"


def run_suite(schema: dict, prompts: list[str], client, n_runs: int = 10,
              repair_mode: str = "local", structured: str = "none",
              temperature: float = 0.7) -> dict:
    """repair_mode: none | local (syntax fixes, free) | model (local + at most one extra model call)."""
    validator = make_validator(schema)
    system = build_system_prompt(schema)
    trials: list[dict] = []
    parsed_by_prompt: dict[int, list] = defaultdict(list)

    for p_index, prompt in enumerate(prompts):
        for run in range(n_runs):
            started = time.perf_counter()
            error = None
            try:
                raw = client.complete(prompt, system=system, temperature=temperature,
                                      schema=schema, structured=structured)
            except Exception as exc:  # network/HTTP problems are not model failures
                raw, error = "", f"{type(exc).__name__}: {exc}"
            latency = round((time.perf_counter() - started) * 1000)

            trial: dict[str, Any] = {
                "prompt_index": p_index, "run": run, "raw": _clip(raw or ""),
                "latency_ms": latency, "request_error": error, "strict_ok": False,
                "final_ok": False, "violations": [], "repair": None,
            }
            if error:
                trial["violations"] = [{"type": "request_error", "path": "$", "message": error}]
                trials.append(trial)
                continue

            strict = check_output(raw, validator)
            trial["strict_ok"] = strict.ok
            trial["final_ok"] = strict.ok
            trial["violations"] = [v.to_dict() for v in strict.violations]
            parsed = strict.parsed

            if not strict.ok and repair_mode != "none":
                steps: list[str] = []
                fixed = local_repair(raw)
                steps += fixed.steps
                candidate = check_output(fixed.text, validator) if fixed.ok else None
                repaired_text = fixed.text if fixed.ok else None
                if (candidate is None or not candidate.ok) and repair_mode == "model":
                    last = candidate.violations if candidate else strict.violations
                    try:
                        text = client.complete(build_repair_prompt(raw, last), system=system,
                                               temperature=0, schema=schema,
                                               structured=structured, purpose="repair")
                        steps.append("asked the model to correct its output (1 call)")
                        candidate = check_output(text, validator)
                        repaired_text = text
                    except Exception as exc:
                        steps.append(f"model repair failed: {type(exc).__name__}")
                ok = bool(candidate and candidate.ok)
                trial["final_ok"] = ok
                trial["repair"] = {
                    "mode": repair_mode, "ok": ok, "steps": steps,
                    "text": _clip(repaired_text) if repaired_text else None,
                    "violations": [v.to_dict() for v in candidate.violations] if candidate else [],
                }
                if candidate and candidate.parsed is not None:
                    parsed = candidate.parsed
            if parsed is not None:
                parsed_by_prompt[p_index].append(parsed)
            trials.append(trial)

    return {
        "model": getattr(client, "name", "unknown"),
        "settings": {"runs_per_prompt": n_runs, "prompts": len(prompts),
                     "repair_mode": repair_mode, "structured": structured,
                     "temperature": temperature},
        "summary": summarize(trials),
        "consistency": [
            {"prompt_index": i, "prompt": prompts[i], **consistency_report(parsed_by_prompt[i])}
            for i in range(len(prompts))
        ],
        "trials": trials,
    }


def summarize(trials: list[dict]) -> dict:
    completed = [t for t in trials if not t["request_error"]]
    n = len(completed)
    strict = sum(t["strict_ok"] for t in completed)
    final = sum(t["final_ok"] for t in completed)
    failed = n - strict
    types: Counter = Counter()
    for t in trials:
        for kind in {v["type"] for v in t["violations"]}:
            types[kind] += 1
    latencies = sorted(t["latency_ms"] for t in completed)
    ci = wilson_interval(strict, n)
    return {
        "total_trials": len(trials), "completed": n,
        "request_errors": len(trials) - n,
        "strict_passed": strict, "final_passed": final,
        "strict_pass_rate": strict / n if n else None,
        "final_pass_rate": final / n if n else None,
        "strict_pass_ci95": list(ci) if ci else None,
        "repair_recovery_rate": (final - strict) / failed if failed else None,
        "failure_counts": dict(types),
        "avg_latency_ms": round(sum(latencies) / n) if n else None,
        "p95_latency_ms": latencies[min(n - 1, int(0.95 * n))] if n else None,
    }
