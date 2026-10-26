# Hackathon day plan (hacking 10:45 to 4:30, submit by 5:45 PM, last commit before 6:00 PM)

Before the day: create the repo, `pip install -r requirements-dev.txt`, run `pytest -q`, and pull one or two small Ollama models.

| Time | Do this |
|---|---|
| 10:45 to 11:30 | Push this project, rename it, set your team name in LICENSE and README, confirm `python -m contract_tester.cli serve` runs on your machine |
| 11:30 to 12:45 | Switch on real models, tune the example schema and prompts, add a second schema (for example invoice extraction) |
| 2:00 to 3:00 | Run `benchmarks/run_benchmark.py --runs 20` on 2 or 3 real models and keep the table |
| 3:00 to 3:45 | Deploy (Render or Docker host), file the upstream issue or PR |
| 3:45 to 4:30 | README table, screenshots, the 2-page PDF |
| 4:30 to 5:30 | Submit early. After submitting, make no more commits |

Rules from the deck: PDF of at most 2 pages, at least 4 screenshots, a GitHub link, no unnecessary packages in the repo, and a repo freeze after submission.
