import json

from contract_tester.repair import extract_balanced, local_repair

OBJ = {"a": 1, "b": ["x", "y"]}


def test_valid_json_needs_no_steps():
    r = local_repair(json.dumps(OBJ))
    assert r.ok and r.steps == [] and r.parsed == OBJ


def test_strips_code_fence():
    r = local_repair("```json\n" + json.dumps(OBJ) + "\n```")
    assert r.ok and r.parsed == OBJ and "removed markdown code fence" in r.steps


def test_extracts_from_prose():
    r = local_repair("Sure! Here you go:\n" + json.dumps(OBJ) + "\nHope that helps.")
    assert r.ok and r.parsed == OBJ


def test_removes_trailing_comma():
    r = local_repair('{"a": 1, "b": [1, 2,],}')
    assert r.ok and r.parsed == {"a": 1, "b": [1, 2]}


def test_python_literal():
    r = local_repair("{'a': True, 'b': None}")
    assert r.ok and r.parsed == {"a": True, "b": None}


def test_truncated_output_is_not_repaired():
    r = local_repair('{"a": 1, "b": [1, 2')
    assert not r.ok


def test_brackets_inside_strings_are_ignored():
    text = 'Result: {"a": "closing } brace", "b": 2} done'
    assert extract_balanced(text) == '{"a": "closing } brace", "b": 2}'


def test_repair_never_invents_fields():
    r = local_repair('```json\n{"a": 1}\n```')
    assert r.parsed == {"a": 1}


def test_empty_input():
    assert not local_repair("").ok and not local_repair(None).ok
