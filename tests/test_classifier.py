import json

import pytest

from conftest import SCHEMA
from contract_tester.classifier import check_output, make_validator

V = make_validator(SCHEMA)
GOOD = {"category": "bug", "priority": "high", "summary": "crash", "needs_human": True}


def kinds(raw):
    return [v.type for v in check_output(raw, V).violations]


def test_valid_output_passes():
    result = check_output(json.dumps(GOOD), V)
    assert result.ok and result.violations == []


def test_invalid_json_with_hint():
    result = check_output("```json\n" + json.dumps(GOOD) + "\n```", V)
    assert [v.type for v in result.violations] == ["invalid_json"]
    assert "code fence" in result.violations[0].message


@pytest.mark.parametrize("raw", ["", "   ", None])
def test_empty_output(raw):
    assert kinds(raw) == ["empty_output"]


def test_nan_is_not_json():
    assert kinds('{"confidence": NaN}') == ["invalid_json"]


def test_missing_field_reports_the_field_name():
    bad = {k: v for k, v in GOOD.items() if k != "priority"}
    violations = check_output(json.dumps(bad), V).violations
    assert [(v.type, v.path) for v in violations] == [("missing_field", "$.priority")]


def test_wrong_type():
    assert kinds(json.dumps({**GOOD, "needs_human": "yes"})) == ["wrong_type"]


def test_bool_is_not_a_number():
    assert kinds(json.dumps({**GOOD, "confidence": True})) == ["wrong_type"]


def test_invalid_enum():
    assert kinds(json.dumps({**GOOD, "category": "other"})) == ["invalid_enum"]


def test_extra_field():
    violations = check_output(json.dumps({**GOOD, "notes": "x"}), V).violations
    assert [(v.type, v.path) for v in violations] == [("extra_field", "$.notes")]


def test_constraint_violation():
    assert kinds(json.dumps({**GOOD, "confidence": 1.5})) == ["constraint_violation"]


def test_nested_path():
    violations = check_output(json.dumps({**GOOD, "tags": ["ok", 3]}), V).violations
    assert [(v.type, v.path) for v in violations] == [("wrong_type", "$.tags[1]")]


def test_non_object_root():
    assert kinds("[1, 2]") == ["wrong_type"]


def test_multiple_failures_are_all_reported():
    bad = {"category": "x", "summary": 5, "needs_human": True, "extra": 1}
    assert set(kinds(json.dumps(bad))) == {"invalid_enum", "wrong_type", "missing_field", "extra_field"}
