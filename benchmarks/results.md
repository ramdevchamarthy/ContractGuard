| Model | Output mode | Trials | Strict pass (95% range) | After syntax repair | Top failure | Avg latency |
|---|---|---|---|---|---|---|
| simulated-sloppy | none | 25 | 24% (11% to 43%) | 56% | invalid_json | 0 ms |
| simulated-sloppy | json_object | 25 | 48% (30% to 67%) | 76% | invalid_json | 0 ms |
| simulated-sloppy | json_schema | 25 | 100% (87% to 100%) | 100% | none | 0 ms |
| simulated-careful | none | 25 | 84% (65% to 94%) | 92% | invalid_json | 0 ms |
| simulated-careful | json_object | 25 | 88% (70% to 96%) | 92% | invalid_json | 0 ms |
| simulated-careful | json_schema | 25 | 100% (87% to 100%) | 100% | none | 0 ms |
| gemma3:4b via Ollama | none | 25 | 0% (0% to 13%) | 100% | invalid_json | 4566 ms |
| gemma3:4b via Ollama | json_object | 25 | 100% (87% to 100%) | 100% | none | 3762 ms |
| gemma3:4b via Ollama | json_schema | 25 | 100% (87% to 100%) | 100% | none | 3759 ms |
