"""FastAPI app: a small JSON API plus the static dashboard."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from jsonschema import SchemaError
from pydantic import BaseModel, Field

from .mock import MockClient
from .runner import OpenAICompatClient, run_suite

BASE = Path(__file__).parent
MAX_TOTAL_CALLS = 500
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "host.docker.internal"}

app = FastAPI(title="Contract Tester", version="0.1.0")


class RunRequest(BaseModel):
    json_schema: dict
    prompts: list[str] = Field(min_length=1, max_length=20)
    provider: Literal["mock", "openai_compat"] = "mock"
    model: str = "sloppy"
    base_url: str | None = None
    api_key: str | None = None
    runs: int = Field(default=10, ge=1, le=50)
    repair_mode: Literal["none", "local", "model"] = "local"
    structured: Literal["none", "json_object", "json_schema"] = "none"
    temperature: float = Field(default=0.7, ge=0, le=2)


def endpoint_allowed(url: str | None) -> bool:
    """SSRF guard: only local endpoints unless ALLOW_REMOTE_ENDPOINTS=1."""
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    if os.environ.get("ALLOW_REMOTE_ENDPOINTS") == "1":
        return True
    return parsed.hostname in LOCAL_HOSTS


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/examples")
def examples():
    schema = json.loads((BASE / "examples" / "support_ticket.schema.json").read_text())
    prompts = json.loads((BASE / "examples" / "support_ticket.prompts.json").read_text())
    return {"schema": schema, "prompts": prompts}


@app.post("/api/run")
def run(req: RunRequest):
    prompts = [p.strip() for p in req.prompts if p.strip()]
    if not prompts:
        raise HTTPException(422, "Add at least one non-empty prompt.")
    if len(prompts) * req.runs > MAX_TOTAL_CALLS:
        raise HTTPException(422, f"Too many calls: prompts x runs must be at most {MAX_TOTAL_CALLS}.")
    if req.provider == "mock":
        client = MockClient(req.json_schema, model=req.model)
    else:
        if not endpoint_allowed(req.base_url):
            raise HTTPException(403, "That endpoint is not allowed. Only localhost endpoints are enabled "
                                     "on this server (set ALLOW_REMOTE_ENDPOINTS=1 to allow others).")
        client = OpenAICompatClient(req.base_url, req.model, req.api_key)
    try:
        return run_suite(req.json_schema, prompts, client, n_runs=req.runs,
                         repair_mode=req.repair_mode, structured=req.structured,
                         temperature=req.temperature)
    except SchemaError as exc:
        raise HTTPException(422, f"The JSON Schema itself is invalid: {exc.message}")


app.mount("/", StaticFiles(directory=BASE / "static", html=True), name="static")
