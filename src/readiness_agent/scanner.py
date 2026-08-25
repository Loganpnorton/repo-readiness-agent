from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .models import Finding, RepositorySnapshot, Severity

IGNORED_DIRS = {".git", ".next", ".venv", "dist", "build", "node_modules", "bin", "obj"}
TEXT_SUFFIXES = {
    ".cs", ".css", ".env", ".go", ".html", ".java", ".js", ".json", ".jsx",
    ".md", ".php", ".py", ".rb", ".rs", ".sh", ".sql", ".toml", ".ts",
    ".tsx", ".yaml", ".yml",
}
LANGUAGE_BY_SUFFIX = {
    ".cs": "C#", ".go": "Go", ".java": "Java", ".js": "JavaScript",
    ".jsx": "JavaScript", ".py": "Python", ".rb": "Ruby", ".rs": "Rust",
    ".ts": "TypeScript", ".tsx": "TypeScript",
}
SECRET_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github-token": re.compile(r"gh[pousr]_[A-Za-z0-9_]{30,}"),
    "stripe-secret": re.compile(r"sk_(?:live|test)_[A-Za-z0-9]{20,}"),
    "aws-access-key": re.compile(r"AKIA[0-9A-Z]{16}"),
}


def iter_files(root: Path):
    for path in root.rglob("*"):
        if path.is_file() and not any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            yield path


def _has_any(root: Path, patterns: tuple[str, ...]) -> bool:
    return any(any(path.match(pattern) for pattern in patterns) for path in iter_files(root))


def scan_repository(root: Path) -> tuple[RepositorySnapshot, list[Finding]]:
    files = list(iter_files(root))
    names = {path.name.lower() for path in files}
    languages = Counter(
        LANGUAGE_BY_SUFFIX[path.suffix.lower()]
        for path in files
        if path.suffix.lower() in LANGUAGE_BY_SUFFIX
    )
    snapshot = RepositorySnapshot(
        name=root.name,
        path=str(root),
        languages=dict(languages),
        files_scanned=len(files),
        has_readme=any(name.startswith("readme") for name in names),
        has_license=any(name.startswith("license") or name == "copying" for name in names),
        has_ci=(root / ".github" / "workflows").is_dir(),
        has_tests=_has_any(root, ("test_*.py", "*_test.py", "*.test.ts", "*.test.tsx", "*Tests.cs")),
        has_demo_media=_has_any(root, ("*.mp4", "*.webm", "*.gif")),
    )
    findings: list[Finding] = []
    checks = [
        (snapshot.has_readme, "portfolio.readme", Severity.high, "README is missing", "Add an outcome-led README with setup and architecture."),
        (snapshot.has_ci, "engineering.ci", Severity.high, "CI workflow is missing", "Run tests and static checks on pull requests."),
        (snapshot.has_tests, "engineering.tests", Severity.high, "Automated tests are missing", "Cover the highest-risk domain transitions."),
        (snapshot.has_demo_media, "portfolio.demo", Severity.medium, "Demo media is missing", "Add a short walkthrough and representative screenshot."),
        (snapshot.has_license, "governance.license", Severity.low, "License is unspecified", "Add a license only when ownership and reuse rights are clear."),
    ]
    for present, rule_id, severity, title, remediation in checks:
        if not present:
            findings.append(Finding(rule_id=rule_id, severity=severity, title=title, evidence=f"No matching artifact found under {root.name}", remediation=remediation))

    for path in files:
        if path.suffix.lower() not in TEXT_SUFFIXES or path.stat().st_size > 1_000_000:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for rule_id, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                findings.append(Finding(
                    rule_id=f"security.{rule_id}", severity=Severity.critical,
                    title="Potential credential committed", evidence="Pattern match; value intentionally redacted",
                    path=str(path.relative_to(root)), remediation="Revoke the credential, remove it from history, and use an environment variable.",
                ))
    return snapshot, findings


def readiness_score(findings: list[Finding]) -> int:
    penalties = {Severity.critical: 35, Severity.high: 15, Severity.medium: 8, Severity.low: 3, Severity.info: 0}
    return max(0, 100 - sum(penalties[f.severity] for f in findings))

