import json

from conftest import SCHEMA
from contract_tester.mock import MockClient, example_from_schema
from contract_tester.classifier import make_validator, check_output
from contract_tester.runner import run_suite, wilson_interval
import random

GOOD = json.dumps({"category": "bug", "priority": "high", "summary": "crash", "needs_human": True})


class Scripted:
    name = "scripted"

    def __init__(self, outputs, repair=None):
        self.outputs, self.repair, self.i = outputs, repair, 0

    def complete(self, prompt, system=None, temperature=0.7, schema=None, structured="none", purpose="generate"):
        if purpose == "repair":
            return self.repair
        out = self.outputs[self.i % len(self.outputs)]
        self.i += 1
        if isinstance(out, Exception):
            raise out
        return out


def test_wilson_matches_known_value():
    low, high = wilson_interval(8, 10)
    assert abs(low - 0.4902) < 1e-3 and abs(high - 0.9433) < 1e-3
    assert wilson_interval(0, 0) is None


def test_counts_and_local_repair():
    client = Scripted([GOOD, "```json\n" + GOOD + "\n```", '{"category": "bug"}'])
    report = run_suite(SCHEMA, ["p"], client, n_runs=3, repair_mode="local")
    s = report["summary"]
    assert (s["strict_passed"], s["final_passed"]) == (1, 2)
    assert s["repair_recovery_rate"] == 0.5
    assert s["failure_counts"] == {"invalid_json": 1, "missing_field": 1}


def test_repair_off():
    client = Scripted([GOOD, "```json\n" + GOOD + "\n```"])
    s = run_suite(SCHEMA, ["p"], client, n_runs=2, repair_mode="none")["summary"]
    assert s["final_passed"] == s["strict_passed"] == 1


def test_model_repair_is_one_extra_call():
    client = Scripted(['{"category": "bug"}'], repair=GOOD)
    report = run_suite(SCHEMA, ["p"], client, n_runs=1, repair_mode="model")
    assert report["summary"]["final_passed"] == 1
    assert report["trials"][0]["repair"]["steps"][-1].startswith("asked the model")


def test_request_errors_are_excluded_from_rates():
    client = Scripted([GOOD, ConnectionError("down")])
    s = run_suite(SCHEMA, ["p"], client, n_runs=2)["summary"]
    assert s["completed"] == 1 and s["request_errors"] == 1 and s["strict_pass_rate"] == 1.0


def test_mock_is_deterministic_and_clean_outputs_validate():
    a = [MockClient(SCHEMA, "careful").complete("x") for _ in range(1)]
    b = [MockClient(SCHEMA, "careful").complete("x") for _ in range(1)]
    assert a == b
    validator = make_validator(SCHEMA)
    for seed in range(30):
        example = example_from_schema(SCHEMA, random.Random(seed))
        assert check_output(json.dumps(example), validator).ok


def test_schema_constrained_mode_never_fails_with_mock():
    report = run_suite(SCHEMA, ["p"], MockClient(SCHEMA, "sloppy"), n_runs=20, structured="json_schema")
    assert report["summary"]["strict_pass_rate"] == 1.0


def test_sloppy_is_worse_than_careful():
    sloppy = run_suite(SCHEMA, ["p"], MockClient(SCHEMA, "sloppy"), n_runs=40, repair_mode="none")
    careful = run_suite(SCHEMA, ["p"], MockClient(SCHEMA, "careful"), n_runs=40, repair_mode="none")
    assert sloppy["summary"]["strict_pass_rate"] < careful["summary"]["strict_pass_rate"]
