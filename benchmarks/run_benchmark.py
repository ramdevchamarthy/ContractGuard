"""Run the contract against every enabled model in models.json and write a Markdown table.

Usage:  python benchmarks/run_benchmark.py --runs 20
Set "enabled": true for the real models you have pulled in Ollama.
Rows labelled simulated-* come from the offline mock and are NOT real model results.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from contract_tester.mock import MockClient  # noqa: E402
from contract_tester.runner import OpenAICompatClient, run_suite  # noqa: E402

EX = ROOT / "contract_tester" / "examples"


def pct(v):
    return "n/a" if v is None else f"{v * 100:.0f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=20)
    ap.add_argument("--schema", default=str(EX / "support_ticket.schema.json"))
    ap.add_argument("--prompts", default=str(EX / "support_ticket.prompts.json"))
    args = ap.parse_args()

    schema = json.loads(Path(args.schema).read_text())
    prompts = json.loads(Path(args.prompts).read_text())
    models = [m for m in json.loads((ROOT / "benchmarks" / "models.json").read_text()) if m.get("enabled")]

    rows, raw = [], []
    for m in models:
        for structured in ("none", "json_object", "json_schema"):
            client = (MockClient(schema, m["model"]) if m["provider"] == "mock"
                      else OpenAICompatClient(m["base_url"], m["model"]))
            rep = run_suite(schema, prompts, client, n_runs=args.runs, repair_mode="local", structured=structured)
            s = rep["summary"]
            ci = s["strict_pass_ci95"]
            worst = max(s["failure_counts"].items(), key=lambda kv: kv[1])[0] if s["failure_counts"] else "none"
            rows.append(f"| {m['label']} | {structured} | {s['completed']} | {pct(s['strict_pass_rate'])} "
                        f"({pct(ci[0]) if ci else 'n/a'} to {pct(ci[1]) if ci else 'n/a'}) | "
                        f"{pct(s['final_pass_rate'])} | {worst} | {s['avg_latency_ms']} ms |")
            raw.append({"label": m["label"], "structured": structured, "summary": s})
            print(rows[-1], flush=True)

    header = ("| Model | Output mode | Trials | Strict pass (95% range) | After syntax repair | Top failure | Avg latency |\n"
              "|---|---|---|---|---|---|---|\n")
    (ROOT / "benchmarks" / "results.md").write_text(header + "\n".join(rows) + "\n")
    (ROOT / "benchmarks" / "results.json").write_text(json.dumps(raw, indent=2))
    print("\nWrote benchmarks/results.md and benchmarks/results.json")


if __name__ == "__main__":
    main()
