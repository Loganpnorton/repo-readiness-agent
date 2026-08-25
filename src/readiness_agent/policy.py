from __future__ import annotations

from .models import ProposedAction

READ_ONLY_ACTIONS = {"report", "inspect", "recommend"}


class PolicyViolation(RuntimeError):
    pass


def authorize(action: ProposedAction, approval_token: str | None = None) -> None:
    if action.kind in READ_ONLY_ACTIONS and not action.mutates:
        return
    expected = f"approve:{action.id}"
    if not action.approved or approval_token != expected:
        raise PolicyViolation(
            f"Mutation '{action.kind}' is blocked until a human approves action {action.id}."
        )

