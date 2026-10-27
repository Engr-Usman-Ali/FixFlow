"""Query helpers shared by several routers: company isolation and visibility rules."""
from datetime import datetime, time, timedelta, timezone
from typing import Optional, TypeVar

from sqlalchemy import Select, and_, false, or_, select
from sqlalchemy.orm import Session

from ..deps import permissions_of
from ..enums import Permission as P
from ..enums import Priority
from ..models import MaintenanceRequest as MR
from ..models import RoleRecord, SlaPolicy, User
from ..rbac import ROLE_PERMISSIONS
from ..workflow import FINISHED_STATES
from .org_setup import default_sla

M = TypeVar("M")


def in_company(db: Session, model: type[M], obj_id: Optional[int], organization_id: int) -> Optional[M]:
    """Load a company-owned row by id, or None if it belongs to another company.

    Rows from other companies look exactly like missing rows, so ids cannot be
    probed across companies (BR-008).
    """
    if obj_id is None:
        return None
    obj = db.get(model, obj_id)
    if obj is None or getattr(obj, "organization_id", None) != organization_id:
        return None
    return obj


def sla_for(db: Session, organization_id: int) -> dict[Priority, int]:
    rows = db.scalars(select(SlaPolicy).where(SlaPolicy.organization_id == organization_id))
    sla = default_sla()
    sla.update({r.priority: r.target_hours for r in rows})
    return sla


def visible_requests(user: User) -> Select:
    """Requests this user may see: own company only, then by permission (FR-073, DR-6.4)."""
    query = select(MR).where(MR.organization_id == user.organization_id)
    perms = permissions_of(user)
    if P.REQUEST_VIEW_ALL in perms:
        return query
    scopes = []
    if P.REQUEST_VIEW_OWN in perms:
        scopes.append(MR.creator_id == user.id)
    if P.REQUEST_VIEW_ASSIGNED in perms:
        scopes.append(MR.technician_id == user.id)
    return query.where(or_(*scopes) if scopes else false())


def can_view(user: User, req: MR) -> bool:
    if req.organization_id != user.organization_id:
        return False
    perms = permissions_of(user)
    return (
        P.REQUEST_VIEW_ALL in perms
        or (P.REQUEST_VIEW_OWN in perms and req.creator_id == user.id)
        or (P.REQUEST_VIEW_ASSIGNED in perms and req.technician_id == user.id)
    )


def overdue_clause(sla: dict[Priority, int], now: Optional[datetime] = None):
    """SQL version of workflow.is_overdue for one company's service targets."""
    now = now or datetime.now(timezone.utc)
    late = [and_(MR.priority == p, MR.created_at < now - timedelta(hours=h)) for p, h in sla.items()]
    return and_(MR.status.notin_(list(FINISHED_STATES)), or_(*late))


def users_with(db: Session, organization_id: int, permission: P) -> list[User]:
    """Active users of a company whose role grants a permission (e.g. managers to notify)."""
    roles = [r for r, perms in ROLE_PERMISSIONS.items() if permission in perms]
    query = (
        select(User)
        .join(RoleRecord, User.role_id == RoleRecord.id)
        .where(User.organization_id == organization_id, User.is_active.is_(True), RoleRecord.name.in_(roles))
    )
    return list(db.scalars(query))


def end_of_day(value: datetime) -> datetime:
    """Treat a plain date as the whole day (date pickers send midnight)."""
    if value.time() == time(0, 0):
        return datetime.combine(value.date(), time.max, tzinfo=value.tzinfo or timezone.utc)
    return value
