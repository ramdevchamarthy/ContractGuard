# Submission PDF template (maximum 2 pages, then at least 4 screenshots and the GitHub link)

**Team name:**
**Members:** name, registration number, email (one line each)
**Challenge:** 12. Structured Output Contract Tester
**Repository:** https://github.com/<you>/<repo>   **Live demo:** <link>

## Problem and approach (about one page)
- Problem: apps break when an LLM returns invalid JSON or a wrong shape.
- Our approach: run N trials per prompt, classify every failure into a fixed taxonomy with JSON paths, measure consistency across runs, apply bounded repair, and report pass rates with confidence intervals.
- What makes it different: repair that never hides schema errors, honest statistics, comparison of prompt-only vs JSON mode vs constrained decoding, and a CI gate.
- Upstream projects used: jsonschema, FastAPI, Pydantic, Ollama (name and license).

## Results (about half a page)
Paste your real benchmark table from `benchmarks/results.md` and one sentence of insight, for example which failure type dominated and how much repair or constrained decoding helped.

## Testing and evidence (a few lines)
Number of tests, what they cover, and the command to reproduce: `pytest -q`.

## Screenshots (minimum 4)
1. Dashboard with a finished run (trial strip and verdict)
2. Failure breakdown and consistency table
3. Trial inspector showing a violation and the raw output
4. CLI or CI gate output (pass and fail)
