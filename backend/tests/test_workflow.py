"""Unit tests for the pure business rules, RBAC matrix and password hashing (no HTTP)."""
import os
from datetime import datetime, timedelta, timezone

import pytest

from app.enums import Permission as P
from app.enums import Priority, Role, Status
from app.rbac import permissions_for
from app.security import hash_password, password_problem, verify_password
from app.services.gemini import AIUnavailable, parse_suggestion
from app.workflow import allowed_targets, can_transition, completion_ok, is_overdue, requires_reason

MANAGER = permissions_for(Role.MANAGER)
TECH = permissions_for(Role.TECHNICIAN)
EMPLOYEE = permissions_for(Role.EMPLOYEE)
ADMIN = permissions_for(Role.ADMIN)
SLA = {Priority.CRITICAL: 24, Priority.HIGH: 72, Priority.MEDIUM: 168, Priority.LOW: 336}


def test_only_close_permission_can_close():
    assert can_transition(Status.RESOLVED, Status.CLOSED, MANAGER, is_assignee=False)
    assert not can_transition(Status.RESOLVED, Status.CLOSED, TECH, is_assignee=True)
    assert not can_transition(Status.RESOLVED, Status.CLOSED, EMPLOYEE, is_assignee=False)


def test_technician_works_only_on_own_assignment():
    assert can_transition(Status.ASSIGNED, Status.IN_PROGRESS, TECH, is_assignee=True)
    assert not can_transition(Status.ASSIGNED, Status.IN_PROGRESS, TECH, is_assignee=False)
    assert can_transition(Status.ASSIGNED, Status.IN_PROGRESS, MANAGER, is_assignee=False)  # work_any


def test_admin_has_no_workflow_powers():
    for current in Status:
        assert allowed_targets(current, ADMIN, is_assignee=False) == []
    assert P.USER_MANAGE in ADMIN and P.REQUEST_VIEW_ALL not in ADMIN


def test_invalid_jump_is_rejected():
    assert not can_transition(Status.NEW, Status.CLOSED, MANAGER, is_assignee=False)
    assert Status.CLOSED in allowed_targets(Status.RESOLVED, MANAGER, is_assignee=False)


def test_reason_rules():
    assert requires_reason(Status.IN_PROGRESS, Status.ON_HOLD)
    assert requires_reason(Status.NEW, Status.REJECTED)
    assert requires_reason(Status.CLOSED, Status.UNDER_REVIEW)  # reopen
    assert not requires_reason(Status.ASSIGNED, Status.IN_PROGRESS)


def test_completion_rule():
    assert not completion_ok("done")
    assert completion_ok("Replaced the fuse and tested.")


def test_overdue_uses_company_service_targets():
    created = datetime.now(timezone.utc) - timedelta(hours=30)
    assert is_overdue(Status.IN_PROGRESS, created, Priority.CRITICAL, SLA)
    assert not is_overdue(Status.IN_PROGRESS, created, Priority.MEDIUM, SLA)
    assert not is_overdue(Status.RESOLVED, created, Priority.CRITICAL, SLA)
    assert not is_overdue(Status.IN_PROGRESS, created, Priority.CRITICAL, {**SLA, Priority.CRITICAL: 48})


def test_password_hash_uses_random_salt():
    a, b = hash_password("Same#Pass1"), hash_password("Same#Pass1")
    assert a.salt != b.salt and a.hash != b.hash
    assert verify_password("Same#Pass1", a.hash, a.salt, a.iterations)
    assert not verify_password("same#pass1", a.hash, a.salt, a.iterations)
    assert int(os.environ["PASSWORD_HASH_ITERATIONS"]) == a.iterations


def test_password_rules():
    assert password_problem("short") is not None
    assert password_problem("alllowercase1") is not None
    assert password_problem("Good#Pass1") is None


class _Cat:
    def __init__(self, id, name):
        self.id, self.name = id, name


def test_ai_output_is_validated_against_company_categories():
    cats = [_Cat(1, "HVAC"), _Cat(2, "Electrical")]
    ok = parse_suggestion('{"category":"hvac","priority":"High","rationale":"No cooling."}', cats)
    assert ok["category_id"] == 1 and ok["priority"] == Priority.HIGH
    with pytest.raises(AIUnavailable):
        parse_suggestion('{"category":"Magic","priority":"High","rationale":"x"}', cats)
    with pytest.raises(AIUnavailable):
        parse_suggestion("not json", cats)
