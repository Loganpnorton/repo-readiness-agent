from pathlib import Path

from readiness_agent.models import Severity
from readiness_agent.scanner import readiness_score, scan_repository


def test_scanner_reports_missing_quality_signals(tmp_path: Path):
    (tmp_path / "app.py").write_text("print('hello')", encoding="utf-8")
    snapshot, findings = scan_repository(tmp_path)
    assert snapshot.languages == {"Python": 1}
    assert {finding.rule_id for finding in findings} >= {"portfolio.readme", "engineering.ci", "engineering.tests"}
    assert readiness_score(findings) < 70


def test_scanner_redacts_detected_secret(tmp_path: Path):
    synthetic_secret = "sk_" + "test_" + ("1" * 24)
    (tmp_path / "README.md").write_text(f"demo {synthetic_secret}", encoding="utf-8")
    _, findings = scan_repository(tmp_path)
    secret = next(finding for finding in findings if finding.severity == Severity.critical)
    assert "123456" not in secret.evidence
    assert secret.path == "README.md"


def test_scanner_recognizes_portfolio_artifacts(tmp_path: Path):
    (tmp_path / "README.md").write_text("# Demo", encoding="utf-8")
    (tmp_path / "LICENSE").write_text("MIT", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: ci", encoding="utf-8")
    (tmp_path / "test_app.py").write_text("def test_ok(): assert True", encoding="utf-8")
    (tmp_path / "demo.gif").write_bytes(b"GIF89a")
    snapshot, findings = scan_repository(tmp_path)
    assert snapshot.has_readme and snapshot.has_license and snapshot.has_ci
    assert snapshot.has_tests and snapshot.has_demo_media
    assert findings == []
