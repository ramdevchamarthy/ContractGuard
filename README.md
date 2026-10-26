# Contract Tester

**Does your LLM keep its JSON promises?** Give Contract Tester a JSON Schema and some prompts. It calls your model many times, checks every answer against the schema, and tells you exactly *how* and *how often* the model breaks the contract, so you can find out before your pipeline does.

Built for the Infinity AI Forge hackathon (Hacktoberfest Hack Day, challenge 12: Structured Output Contract Tester).

## Why this matters

Apps that depend on model output being valid JSON fail on a single stray code fence, trailing comma, missing field or out-of-range enum value. Teams usually discover this in production. Contract Tester turns "it seems to work" into a measured pass rate with a failure breakdown.

## What it does

| Capability | How |
|---|---|
| Detect invalid JSON | Strict parse, rejects `NaN`/`Infinity`, and explains the likely cause (code fence, prose prefix, trailing comma, single quotes, truncation) |
| Detect schema violations | Missing fields, wrong types, invalid enum values, extra fields, and other constraint violations, each with a JSON path (for example `$.tags[1]`) |
| Detect inconsistent output | Compares the *shape* of outputs across runs of the same prompt and lists fields that appear, vanish or change type |
| Bounded repair (optional) | `local`: free, deterministic syntax fixes that never change data. `model`: local fixes, then at most **one** extra model call |
| Evidence | Strict pass rate with a 95% Wilson confidence interval, repair recovery rate, failure counts, latency |
| Compare output modes | Prompt only vs JSON mode vs schema-constrained decoding |
| CI gate | `contract-tester run --min-pass-rate 0.9` exits non-zero when a model regresses |

## Quick start

```bash
git clone <your-repo-url> && cd contract-tester
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# web dashboard at http://127.0.0.1:8000
python -m contract_tester.cli serve
```

Open the page and press **Run trials**. It starts with a simulated model, so it works with no setup. The simulated model breaks the contract on purpose with a fixed random seed. **Its numbers are illustrative and are not a real benchmark.**

### Test a real model with Ollama

```bash
ollama pull gemma3:4b
```

In the dashboard choose **Real model**, keep the endpoint `http://localhost:11434/v1`, and set the model name. Any OpenAI-compatible server works (Ollama, vLLM, llama.cpp server, LM Studio).

### Command line and CI

```bash
python -m contract_tester.cli run \
  --schema contract_tester/examples/support_ticket.schema.json \
  --prompts contract_tester/examples/support_ticket.prompts.json \
  --provider openai_compat --model gemma3:4b --runs 20 \
  --repair local --min-pass-rate 0.9 --out report.json
```

Exit codes: `0` pass, `1` below the threshold, `2` invalid schema. Add `--gate final` to gate on the pass rate after repair instead of the strict rate. A ready-made GitHub Actions workflow is in `.github/workflows/ci.yml`.

### Benchmark several models

Set `"enabled": true` for the models you have pulled in `benchmarks/models.json`, then:

```bash
python benchmarks/run_benchmark.py --runs 20
```

This writes `benchmarks/results.md` and `results.json`. Paste your real table below before submitting.

| Model | Output mode | Trials | Strict pass (95% range) | After syntax repair | Top failure | Avg latency |
|---|---|---|---|---|---|---|
| _fill in from your own run_ | | | | | | |

## How it works

```
schema + prompts ──► runner ──► model (OpenAI-compatible endpoint)
                       │
                       ▼
        classifier (jsonschema + failure taxonomy)
                       │ fails
                       ▼
        repair: local syntax fixes ──► (optional) one model retry
                       │
                       ▼
   summary + Wilson CI + consistency report ──► dashboard / CLI / JSON
```

- `contract_tester/classifier.py`: strict parsing and mapping of `jsonschema` errors to eight failure types.
- `contract_tester/repair.py`: string-aware JSON extraction and syntax repair.
- `contract_tester/consistency.py`: shape signatures and cross-run comparison.
- `contract_tester/runner.py`: the trial loop, OpenAI-compatible client and statistics.
- `contract_tester/mock.py`: seeded offline model for demos and tests.
- `contract_tester/server.py`, `static/index.html`: the API and dashboard.

### Failure taxonomy

`invalid_json`, `empty_output`, `missing_field`, `wrong_type`, `invalid_enum`, `extra_field`, `constraint_violation`, `request_error`. Request errors (network or HTTP problems) are reported but excluded from pass rates, because they are not the model breaking its contract.

### Design decisions

- **Repair never hides schema problems.** Local repair only fixes syntax. A missing field is still a failure unless the single model retry fixes it.
- **Honest statistics.** Pass rates come with a Wilson interval so a 10-trial result is not mistaken for certainty.
- **Safe to deploy.** The server only calls `localhost` endpoints unless `ALLOW_REMOTE_ENDPOINTS=1`, which blocks server-side request forgery. Total calls per request are capped, and API keys are never stored or logged. Raw model output is rendered as text, never as HTML.

## Tests

```bash
pytest -q
```

Covers the classifier (every failure type and JSON paths), repair, consistency detection, the statistics, the runner with scripted models, and the API including the endpoint allow-list.

## Deployment

```bash
docker build -t contract-tester . && docker run -p 8000:8000 contract-tester
```

`render.yaml` deploys the Docker image on Render's free tier. Add the live URL here: **<your-live-link>**.

## Limitations

- The simulated model produces illustrative numbers only.
- Local repair handles syntax, not meaning. The classifier relies on `jsonschema` for validation semantics, so it supports what Draft 2020-12 supports.
- The mock generator builds samples from simple schemas (types, enums, bounds). It ignores `pattern` and `format`.

## Upstream projects and licenses

Built on [jsonschema](https://github.com/python-jsonschema/jsonschema) (MIT), [FastAPI](https://github.com/fastapi/fastapi) (MIT), [Pydantic](https://github.com/pydantic/pydantic) (MIT), [Requests](https://github.com/psf/requests) (Apache-2.0), and works with [Ollama](https://github.com/ollama/ollama) (MIT) and any OpenAI-compatible server. See `docs/UPSTREAM_CONTRIBUTIONS.md` for what we contributed back.

## License

MIT
