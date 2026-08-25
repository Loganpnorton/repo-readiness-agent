from pathlib import Path

import pytest

from readiness_agent.agent import ReadinessAgent
from readiness_agent.models import ProposedAction, safe_repo_path
from readiness_agent.planner import OpenAIPlanner
from readiness_agent.policy import PolicyViolation, authorize
from readiness_agent.store import RunStore


def test_agent_persists_replayable_run(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# Synthetic", encoding="utf-8")
    store = RunStore(tmp_path / "runs")
    run = ReadinessAgent(store).audit(repo)
    restored = store.get(run.id)
    assert restored.id == run.id
    assert restored.trace[0]["step"] == "scan"
    assert all(not action.mutates for action in restored.proposed_actions)


def test_mutation_requires_exact_human_approval_token():
    action = ProposedAction(kind="write_file", title="Add CI", rationale="Missing", target="ci.yml")
    with pytest.raises(PolicyViolation):
        authorize(action)
    action.approved = True
    with pytest.raises(PolicyViolation):
        authorize(action, "approve:wrong")
    authorize(action, f"approve:{action.id}")


def test_read_only_action_needs_no_token():
    action = ProposedAction(kind="recommend", title="Add tests", rationale="Missing", target="tests", mutates=False)
    authorize(action)


def test_store_rejects_path_traversal(tmp_path: Path):
    with pytest.raises(ValueError):
        RunStore(tmp_path).get("../escape")


def test_store_lists_saved_run(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = RunStore(tmp_path / "runs")
    run = ReadinessAgent(store).audit(repo)
    assert store.list() == [{
        "id": run.id,
        "created_at": run.created_at.isoformat().replace("+00:00", "Z"),
        "score": run.score,
        "repository": "repo",
    }]


def test_path_and_model_configuration_fail_closed(tmp_path: Path, monkeypatch):
    assert safe_repo_path(str(tmp_path)) == tmp_path.resolve()
    with pytest.raises(ValueError):
        safe_repo_path(str(tmp_path / "missing"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAIPlanner()
