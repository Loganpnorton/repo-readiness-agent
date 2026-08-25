from __future__ import annotations

from pathlib import Path
from time import perf_counter

from .models import AuditRun
from .planner import DeterministicPlanner, Planner
from .scanner import readiness_score, scan_repository
from .store import RunStore


class ReadinessAgent:
    def __init__(self, store: RunStore, planner: Planner | None = None):
        self.store = store
        self.planner = planner or DeterministicPlanner()

    def audit(self, root: Path) -> AuditRun:
        started = perf_counter()
        snapshot, findings = scan_repository(root)
        scan_ms = round((perf_counter() - started) * 1000, 2)
        plan_started = perf_counter()
        actions = self.planner.propose(findings)
        plan_ms = round((perf_counter() - plan_started) * 1000, 2)
        run = AuditRun(
            snapshot=snapshot,
            score=readiness_score(findings),
            findings=findings,
            proposed_actions=actions,
            planner=self.planner.name,
            trace=[
                {"step": "scan", "latency_ms": scan_ms, "files": snapshot.files_scanned},
                {"step": "plan", "latency_ms": plan_ms, "actions": len(actions)},
                {"step": "policy", "mutations_executed": 0, "approval_required": True},
            ],
        )
        self.store.save(run)
        return run

