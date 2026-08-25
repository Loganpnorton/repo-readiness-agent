from __future__ import annotations

import json
from pathlib import Path

from .models import AuditRun


class RunStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, run: AuditRun) -> Path:
        destination = self.root / f"{run.id}.json"
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(run.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(destination)
        return destination

    def get(self, run_id: str) -> AuditRun:
        safe_id = Path(run_id).name
        if safe_id != run_id:
            raise ValueError("Invalid run id")
        return AuditRun.model_validate_json((self.root / f"{safe_id}.json").read_text(encoding="utf-8"))

    def list(self) -> list[dict[str, object]]:
        summaries = []
        for path in sorted(self.root.glob("*.json"), reverse=True):
            payload = json.loads(path.read_text(encoding="utf-8"))
            summaries.append({"id": payload["id"], "created_at": payload["created_at"], "score": payload["score"], "repository": payload["snapshot"]["name"]})
        return summaries

