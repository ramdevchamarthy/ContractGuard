# Upstream contribution plan (open-source value is 25% of the score)

Judges ask: "Does the result meaningfully extend, integrate, test, or improve existing software?"
Do at least one of these during the day, and link it in your README and PDF.

1. **Integrate** (already done): jsonschema for validation, FastAPI/Pydantic for the API, any OpenAI-compatible server for models.
2. **Report real findings upstream.** If your benchmark shows a model or server fails `response_format: json_schema` on a specific schema feature, open a well-written issue on that project (Ollama, llama.cpp, vLLM) with a minimal reproduction from your report.json.
3. **Contribute a small fix or docs PR** to jsonschema, Ollama docs or a structured-output library such as Outlines or Instructor (for example a missing example, a clearer error message, or a test case you found).
4. **Publish the reusable core.** `contract_tester/` is pip-installable (`pip install .`) with a CLI, so other developers can use it in their CI.
5. **Ship a GitHub Action example** (`.github/workflows/ci.yml`) that others can copy.

Record here what you did, with links:

- [ ] Issue or PR link 1:
- [ ] Issue or PR link 2:
