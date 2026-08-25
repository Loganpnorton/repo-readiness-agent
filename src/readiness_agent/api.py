from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .agent import ReadinessAgent
from .models import AuditRequest, AuditRun, safe_repo_path
from .planner import OpenAIPlanner
from .store import RunStore

PACKAGE_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = PACKAGE_ROOT / "static"
DATA_ROOT = Path(os.getenv("READINESS_DATA_DIR", ".repo-readiness/runs"))

app = FastAPI(title="Repo Readiness Agent", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")


def make_agent(use_model: bool) -> ReadinessAgent:
    planner = OpenAIPlanner() if use_model else None
    return ReadinessAgent(RunStore(DATA_ROOT), planner)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_ROOT / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "policy-gated"}


@app.post("/api/audits", response_model=AuditRun)
def create_audit(request: AuditRequest):
    try:
        return make_agent(request.use_model).audit(safe_repo_path(request.path))
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/audits")
def list_audits():
    return RunStore(DATA_ROOT).list()

