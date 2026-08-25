from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class Finding(BaseModel):
    rule_id: str
    severity: Severity
    title: str
    evidence: str
    path: str | None = None
    remediation: str


class RepositorySnapshot(BaseModel):
    name: str
    path: str
    languages: dict[str, int] = Field(default_factory=dict)
    files_scanned: int = 0
    has_readme: bool = False
    has_license: bool = False
    has_ci: bool = False
    has_tests: bool = False
    has_demo_media: bool = False


class ProposedAction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    kind: str
    title: str
    rationale: str
    target: str
    mutates: bool = True
    approved: bool = False


class AuditRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    snapshot: RepositorySnapshot
    score: int
    findings: list[Finding]
    proposed_actions: list[ProposedAction]
    planner: str
    trace: list[dict[str, Any]] = Field(default_factory=list)


class AuditRequest(BaseModel):
    path: str
    use_model: bool = False


def safe_repo_path(raw: str) -> Path:
    path = Path(raw).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        raise ValueError("Repository path must be an existing directory")
    return path

