"""Company audit log for System Administrators (FR-100, FR-101, open question 11)."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import require_permission
from ..enums import Permission as P
from ..models import AuditEvent, User
from ..schemas import AuditEventOut, Page, UserBrief
from ..services.queries import end_of_day

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=Page[AuditEventOut])
def list_audit(
    action: Optional[str] = Query(default=None, max_length=40, description="Prefix such as 'user.' or 'settings.'"),
    actor_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission(P.AUDIT_VIEW)),
):
    # The company is reached through the acting user (see models.AuditEvent).
    query = (
        select(AuditEvent)
        .join(User, AuditEvent.actor_id == User.id)
        .where(User.organization_id == admin.organization_id)
    )
    if action:
        query = query.where(AuditEvent.action.startswith(action.strip()))
    if actor_id:
        query = query.where(AuditEvent.actor_id == actor_id)
    if date_from:
        query = query.where(AuditEvent.created_at >= date_from)
    if date_to:
        query = query.where(AuditEvent.created_at <= end_of_day(date_to))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.options(joinedload(AuditEvent.actor), joinedload(AuditEvent.target_user), joinedload(AuditEvent.request))
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).unique()
    items = [
        AuditEventOut(
            id=e.id,
            action=e.action,
            detail=e.detail,
            created_at=e.created_at,
            actor=UserBrief.model_validate(e.actor),
            target_user=UserBrief.model_validate(e.target_user) if e.target_user else None,
            request_id=e.request_id,
            request_ref=e.request.ref if e.request else None,
        )
        for e in rows
    ]
    return Page[AuditEventOut](items=items, total=total, page=page, page_size=page_size)
