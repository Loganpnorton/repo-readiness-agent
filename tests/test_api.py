from pathlib import Path

from fastapi.testclient import TestClient

from readiness_agent import api


def test_health():
    client = TestClient(api.app)
    assert client.get("/").status_code == 200
    response = client.get("/api/health")
    assert response.json() == {"status": "ok", "mode": "policy-gated"}


def test_audit_endpoint(tmp_path: Path, monkeypatch):
    repo = tmp_path / "sample"
    repo.mkdir()
    (repo / "main.py").write_text("print('safe')", encoding="utf-8")
    monkeypatch.setattr(api, "DATA_ROOT", tmp_path / "runs")
    response = TestClient(api.app).post("/api/audits", json={"path": str(repo), "use_model": False})
    assert response.status_code == 200
    assert response.json()["snapshot"]["name"] == "sample"
    assert (tmp_path / "runs").is_dir()


def test_audit_rejects_missing_directory(tmp_path: Path):
    response = TestClient(api.app).post("/api/audits", json={"path": str(tmp_path / "missing"), "use_model": False})
    assert response.status_code == 400


def test_list_audits(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(api, "DATA_ROOT", tmp_path / "runs")
    assert TestClient(api.app).get("/api/audits").json() == []
