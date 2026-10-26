import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from conftest import SCHEMA
from contract_tester.server import app, endpoint_allowed

client = TestClient(app)
BODY = {"json_schema": SCHEMA, "prompts": ["a", "b"], "provider": "mock", "model": "sloppy", "runs": 5}


def test_health_and_examples():
    assert client.get("/api/health").json() == {"status": "ok"}
    data = client.get("/api/examples").json()
    assert "schema" in data and data["prompts"]


def test_run_with_mock():
    r = client.post("/api/run", json=BODY)
    assert r.status_code == 200
    data = r.json()
    assert data["summary"]["total_trials"] == 10 and len(data["trials"]) == 10


def test_invalid_schema_is_422():
    r = client.post("/api/run", json={**BODY, "json_schema": {"type": "banana"}})
    assert r.status_code == 422


def test_too_many_calls_is_422():
    r = client.post("/api/run", json={**BODY, "prompts": ["x"] * 20, "runs": 50})
    assert r.status_code == 422


def test_remote_endpoint_is_blocked():
    r = client.post("/api/run", json={**BODY, "provider": "openai_compat", "base_url": "http://169.254.169.254/v1"})
    assert r.status_code == 403


def test_endpoint_allow_list(monkeypatch):
    assert endpoint_allowed("http://localhost:11434/v1")
    assert not endpoint_allowed("http://example.com/v1")
    assert not endpoint_allowed("file:///etc/passwd")
    monkeypatch.setenv("ALLOW_REMOTE_ENDPOINTS", "1")
    assert endpoint_allowed("https://example.com/v1")


def test_index_page_is_served():
    assert "Contract Tester" in client.get("/").text
