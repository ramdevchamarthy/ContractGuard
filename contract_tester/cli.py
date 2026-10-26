"""Command line: `contract-tester run ...` (CI gate) and `contract-tester serve`."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import SchemaError

from .mock import MockClient
from .runner import OpenAICompatClient, run_suite


def load_prompts(path: str) -> list[str]:
    text = Path(path).read_text(encoding="utf-8")
    if path.endswith(".json"):
        return [str(p) for p in json.loads(text)]
    return [line.strip() for line in text.splitlines() if line.strip()]


def pct(value) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def format_report(report: dict) -> str:
    s = report["summary"]
    lines = [
        f"Model: {report['model']}   repair={report['settings']['repair_mode']}   "
        f"structured={report['settings']['structured']}",
        f"Trials: {s['completed']} completed, {s['request_errors']} request errors",
        f"Strict pass rate: {pct(s['strict_pass_rate'])}  "
        f"(95% CI {pct(s['strict_pass_ci95'][0]) if s['strict_pass_ci95'] else 'n/a'} to "
        f"{pct(s['strict_pass_ci95'][1]) if s['strict_pass_ci95'] else 'n/a'})",
        f"Pass rate after repair: {pct(s['final_pass_rate'])}   "
        f"repair recovery: {pct(s['repair_recovery_rate'])}",
        "Failures (trials affected): " + (", ".join(f"{k}={v}" for k, v in sorted(s['failure_counts'].items())) or "none"),
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="contract-tester")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="test a model against a JSON Schema")
    run.add_argument("--schema", required=True)
    run.add_argument("--prompts", required=True, help=".json list or one prompt per line")
    run.add_argument("--provider", choices=["mock", "openai_compat"], default="openai_compat")
    run.add_argument("--model", default="sloppy")
    run.add_argument("--base-url", default="http://localhost:11434/v1")
    run.add_argument("--api-key", default=None)
    run.add_argument("--runs", type=int, default=10)
    run.add_argument("--repair", choices=["none", "local", "model"], default="local")
    run.add_argument("--structured", choices=["none", "json_object", "json_schema"], default="none")
    run.add_argument("--temperature", type=float, default=0.7)
    run.add_argument("--min-pass-rate", type=float, default=None,
                     help="exit 1 if the pass rate is below this (0 to 1)")
    run.add_argument("--gate", choices=["strict", "final"], default="strict")
    run.add_argument("--out", default=None, help="write the full JSON report here")

    serve = sub.add_parser("serve", help="start the web dashboard")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)

    if args.command == "serve":
        import uvicorn
        uvicorn.run("contract_tester.server:app", host=args.host, port=args.port)
        return 0

    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
    prompts = load_prompts(args.prompts)
    client = (MockClient(schema, args.model) if args.provider == "mock"
              else OpenAICompatClient(args.base_url, args.model, args.api_key))
    try:
        report = run_suite(schema, prompts, client, n_runs=args.runs, repair_mode=args.repair,
                           structured=args.structured, temperature=args.temperature)
    except SchemaError as exc:
        print(f"Invalid JSON Schema: {exc.message}", file=sys.stderr)
        return 2
    print(format_report(report))
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.min_pass_rate is not None:
        key = "strict_pass_rate" if args.gate == "strict" else "final_pass_rate"
        rate = report["summary"][key]
        if rate is None or rate < args.min_pass_rate:
            print(f"FAIL: {args.gate} pass rate {pct(rate)} is below {pct(args.min_pass_rate)}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
