from contract_tester.consistency import consistency_report, signature


def test_identical_shapes_score_one():
    r = consistency_report([{"a": 1}, {"a": 2}, {"a": 3}])
    assert r["score"] == 1 and r["unstable_paths"] == []


def test_detects_missing_and_changed_types():
    r = consistency_report([{"a": 1, "b": "x"}, {"a": "1"}, {"a": 2, "b": "y"}])
    paths = {u["path"]: u for u in r["unstable_paths"]}
    assert set(paths) == {"$.a", "$.b"}
    assert paths["$.a"]["types"] == ["integer", "string"]
    assert paths["$.b"]["present_in"] == 2
    assert abs(r["score"] - 2 / 3) < 1e-9


def test_single_run_has_no_score():
    assert consistency_report([{"a": 1}])["score"] is None


def test_bool_and_int_differ():
    assert signature({"a": True}) != signature({"a": 1})


def test_array_items_are_unioned():
    assert ("$.t[]", "string") in signature({"t": ["a", "b"]})
