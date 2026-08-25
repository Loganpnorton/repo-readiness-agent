from __future__ import annotations

import json
import os
from typing import Protocol

import httpx

from .models import Finding, ProposedAction


class Planner(Protocol):
    name: str

    def propose(self, findings: list[Finding]) -> list[ProposedAction]: ...


class DeterministicPlanner:
    name = "deterministic"

    def propose(self, findings: list[Finding]) -> list[ProposedAction]:
        return [
            ProposedAction(
                kind="recommend",
                title=f"Resolve {finding.title.lower()}",
                rationale=finding.remediation,
                target=finding.path or finding.rule_id,
                mutates=False,
            )
            for finding in findings
        ]


class OpenAIPlanner:
    """Optional structured planner using the Responses API; never executes actions."""

    name = "openai-responses"
    endpoint = "https://api.openai.com/v1/responses"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5-mini")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for the model planner")

    def propose(self, findings: list[Finding]) -> list[ProposedAction]:
        schema = {
            "type": "object",
            "properties": {
                "actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "kind": {"type": "string"},
                            "title": {"type": "string"},
                            "rationale": {"type": "string"},
                            "target": {"type": "string"},
                            "mutates": {"type": "boolean"},
                        },
                        "required": ["kind", "title", "rationale", "target", "mutates"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["actions"],
            "additionalProperties": False,
        }
        payload = {
            "model": self.model,
            "instructions": "Prioritize repository readiness. Propose actions only; never claim execution.",
            "input": json.dumps([finding.model_dump(mode="json") for finding in findings]),
            "text": {"format": {"type": "json_schema", "name": "readiness_plan", "strict": True, "schema": schema}},
        }
        response = httpx.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
        parsed = json.loads(body["output"][0]["content"][0]["text"])
        return [ProposedAction(**action) for action in parsed["actions"]]

