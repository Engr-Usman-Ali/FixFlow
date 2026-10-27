"""Helpers that write history, audit rows and notifications.

They only add rows to the session; the calling endpoint commits once, so a
failed operation never leaves a half-updated workflow (NFR-REL-002/003).
"""
from datetime import datetime
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from ..enums import Status
from ..models import AuditEvent, MaintenanceRequest, Notification, StatusHistory, User


def record_status(
    db: Session,
    req: MaintenanceRequest,
    old: Optional[Status],
    new: Status,
    actor: User,
    reason: Optional[str] = None,
    at: Optional[datetime] = None,
) -> None:
    row = StatusHistory(request_id=req.id, old_status=old, new_status=new, changed_by_id=actor.id, reason=reason)
    if at is not None:  # optional back-dated timestamp (data imports)
        row.changed_at = at
    db.add(row)


def record_audit(
    db: Session,
    actor: User,
    action: str,
    detail: str,
    request: Optional[MaintenanceRequest] = None,
    target_user: Optional[User] = None,
) -> None:
    db.add(
        AuditEvent(
            actor_id=actor.id,
            request_id=request.id if request else None,
            target_user_id=target_user.id if target_user else None,
            action=action,
            detail=detail[:2000],
        )
    )


def notify(
    db: Session,
    req: MaintenanceRequest,
    event_type: str,
    message: str,
    recipients: Iterable[Optional[User]],
    actor: User,
) -> None:
    """One in-app notification per unique recipient, never the actor (FR-062).

    Only users of the same company who can already see the request are passed
    in, so the message never exposes details to anyone else (FR-064).
    """
    seen: set[int] = set()
    for user in recipients:
        if (
            user is None
            or user.id == actor.id
            or user.id in seen
            or not user.is_active
            or user.organization_id != req.organization_id
        ):
            continue
        seen.add(user.id)
        db.add(
            Notification(
                recipient_id=user.id,
                request_id=req.id,
                event_type=event_type,
                message=f"{req.ref} · {message}"[:300],
            )
        )
