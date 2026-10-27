"""Pure business rules for the request lifecycle (SRS section 7).

Nothing here touches the database, so every rule is unit tested directly.
Transitions are guarded by permissions, not role names, so changing the RBAC
matrix in rbac.py is enough to change who may do what.
"""
from datetime import datetime, timedelta, timezone
from typing import Collection, Mapping, Optional

from .enums import Permission as P
from .enums import Priority, Status

# current status -> {target status: permission needed}
# Moving New/Under Review/On Hold -> Assigned happens through the assign endpoint.
TRANSITIONS: dict[Status, dict[Status, P]] = {
    Status.NEW: {Status.UNDER_REVIEW: P.REQUEST_REVIEW, Status.ON_HOLD: P.REQUEST_REVIEW, Status.REJECTED: P.REQUEST_REVIEW},
    Status.UNDER_REVIEW: {Status.ON_HOLD: P.REQUEST_REVIEW, Status.REJECTED: P.REQUEST_REVIEW},
    Status.ASSIGNED: {Status.IN_PROGRESS: P.REQUEST_WORK, Status.ON_HOLD: P.REQUEST_WORK, Status.UNDER_REVIEW: P.REQUEST_REVIEW},
    Status.IN_PROGRESS: {Status.RESOLVED: P.REQUEST_WORK, Status.ON_HOLD: P.REQUEST_WORK},
    Status.ON_HOLD: {
        Status.IN_PROGRESS: P.REQUEST_WORK,
        Status.ASSIGNED: P.REQUEST_REVIEW,
        Status.UNDER_REVIEW: P.REQUEST_REVIEW,
    },
    Status.RESOLVED: {Status.CLOSED: P.REQUEST_CLOSE, Status.IN_PROGRESS: P.REQUEST_CLOSE},  # close or send back
    Status.CLOSED: {Status.UNDER_REVIEW: P.REQUEST_CLOSE},  # reopen (FR-043)
    Status.REJECTED: {Status.UNDER_REVIEW: P.REQUEST_CLOSE},  # reopen
}

FINISHED_STATES = frozenset({Status.RESOLVED, Status.CLOSED, Status.REJECTED})
OPEN_STATES = frozenset(set(Status) - FINISHED_STATES)
REVIEW_QUEUE_STATES = (Status.NEW, Status.UNDER_REVIEW)
ASSIGNABLE_STATES = frozenset({Status.NEW, Status.UNDER_REVIEW, Status.ASSIGNED, Status.IN_PROGRESS, Status.ON_HOLD})
WORK_LOG_STATES = frozenset({Status.ASSIGNED, Status.IN_PROGRESS, Status.ON_HOLD})
NEEDS_TECHNICIAN = frozenset({Status.ASSIGNED, Status.IN_PROGRESS})
MIN_COMPLETION_CHARS = 10

# Priority order used for sorting ("desc" = most urgent first).
PRIORITY_RANK: dict[Priority, int] = {Priority.LOW: 1, Priority.MEDIUM: 2, Priority.HIGH: 3, Priority.CRITICAL: 4}


def is_known_transition(current: Status, target: Status) -> bool:
    return target in TRANSITIONS.get(current, {})


def required_permission(current: Status, target: Status) -> Optional[P]:
    return TRANSITIONS.get(current, {}).get(target)


def can_transition(current: Status, target: Status, permissions: Collection[P], is_assignee: bool) -> bool:
    """Work moves need REQUEST_WORK plus being the assignee, or REQUEST_WORK_ANY (FR-036)."""
    needed = required_permission(current, target)
    if needed is None or needed not in permissions:
        return False
    if needed == P.REQUEST_WORK:
        return is_assignee or P.REQUEST_WORK_ANY in permissions
    return True


def allowed_targets(current: Status, permissions: Collection[P], is_assignee: bool) -> list[Status]:
    return [t for t in TRANSITIONS.get(current, {}) if can_transition(current, t, permissions, is_assignee)]


def requires_reason(current: Status, target: Status) -> bool:
    """BR-005 (hold and reject) plus reopening and sending work back (FR-043)."""
    if target in (Status.ON_HOLD, Status.REJECTED):
        return True
    if current in (Status.CLOSED, Status.REJECTED):
        return True
    return current == Status.RESOLVED and target == Status.IN_PROGRESS


def ends_assignment(target: Status) -> bool:
    """Returning a request to review frees it for a fresh assignment."""
    return target == Status.UNDER_REVIEW


def completion_ok(details: Optional[str]) -> bool:
    """BR-004: completion details are required before Resolved."""
    return len((details or "").strip()) >= MIN_COMPLETION_CHARS


def due_at(created_at: datetime, priority: Priority, sla_hours: Mapping[Priority, int]) -> datetime:
    return created_at + timedelta(hours=sla_hours[priority])


def is_overdue(
    status: Status,
    created_at: datetime,
    priority: Priority,
    sla_hours: Mapping[Priority, int],
    now: Optional[datetime] = None,
) -> bool:
    """BR-010: open work past its company's service target is overdue."""
    if status in FINISHED_STATES:
        return False
    now = now or datetime.now(timezone.utc)
    if created_at.tzinfo is None:  # SQLite returns naive datetimes
        created_at = created_at.replace(tzinfo=timezone.utc)
    return now > due_at(created_at, priority, sla_hours)
