"""Dashboard numbers for every role and management reports (FR-080 to FR-085)."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_any_permission, require_permission
from ..enums import Permission as P
from ..enums import Priority, Role, Status
from ..models import AuditEvent, Category, Equipment, Location, MaintenanceRequest as MR, RoleRecord, User
from ..services.queries import end_of_day, overdue_clause, sla_for, visible_requests
from ..services.serializers import request_out
from ..workflow import OPEN_STATES

router = APIRouter(prefix="/reports", tags=["reports"])


def _count(db: Session, query: Select) -> int:
    return db.scalar(select(func.count()).select_from(query.subquery())) or 0


def _by_enum(db: Session, base: Select, column, enum_cls) -> dict[str, int]:
    """Count rows per enum value, including zeros so charts stay stable."""
    sub = base.subquery()
    col = sub.c[column.key]
    found = {(k.value if hasattr(k, "value") else k): n for k, n in db.execute(select(col, func.count()).group_by(col))}
    return {e.value: found.get(e.value, 0) for e in enum_cls}


def _by_lookup(db: Session, base: Select, fk_column, model, organization_id: int) -> dict[str, int]:
    """Count rows per category/location name for this company."""
    sub = base.subquery()
    rows = db.execute(
        select(model.name, func.count(sub.c.id))
        .select_from(model)
        .outerjoin(sub, sub.c[fk_column.key] == model.id)
        .where(model.organization_id == organization_id)
        .group_by(model.name)
        .order_by(func.count(sub.c.id).desc(), model.name)
    )
    return {name: n for name, n in rows if n > 0}


@router.get("/overview")
def overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Role-aware numbers for the dashboard home page (limited to what the user may see)."""
    base = visible_requests(user)
    sla = sla_for(db, user.organization_id)
    by_status = _by_enum(db, base, MR.status, Status)
    recent = db.scalars(base.order_by(MR.updated_at.desc()).limit(6))
    return {
        "total": sum(by_status.values()),
        "open": sum(by_status[s.value] for s in OPEN_STATES),
        "overdue": _count(db, base.where(overdue_clause(sla))),
        "awaiting_review": by_status[Status.NEW.value] + by_status[Status.UNDER_REVIEW.value],
        "awaiting_closure": by_status[Status.RESOLVED.value],
        "by_status": by_status,
        "recent": [request_out(r, sla) for r in recent],
    }


@router.get("/admin-overview")
def admin_overview(
    db: Session = Depends(get_db),
    admin: User = Depends(require_any_permission(P.USER_MANAGE, P.SETTINGS_MANAGE)),
):
    """Administration dashboard: people, configuration and activity. No request details."""
    org_id = admin.organization_id
    users = select(User).where(User.organization_id == org_id)
    role_counts = dict(
        db.execute(
            select(RoleRecord.name, func.count(User.id))
            .join(User, User.role_id == RoleRecord.id)
            .where(User.organization_id == org_id, User.is_active.is_(True))
            .group_by(RoleRecord.name)
        ).all()
    )
    locked = [u for u in db.scalars(users.where(User.locked_until.is_not(None))) if u.is_locked]
    recent_audit = db.execute(
        select(AuditEvent.id, AuditEvent.action, AuditEvent.detail, AuditEvent.created_at, User.name)
        .join(User, AuditEvent.actor_id == User.id)
        .where(User.organization_id == org_id)
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .limit(8)
    ).all()
    requests_base = select(MR).where(MR.organization_id == org_id)
    return {
        "users_total": _count(db, users),
        "users_active": _count(db, users.where(User.is_active.is_(True))),
        "users_locked": len(locked),
        "by_role": {r.value: role_counts.get(r, 0) for r in Role},
        "categories_active": _count(db, select(Category).where(Category.organization_id == org_id, Category.is_active.is_(True))),
        "locations_active": _count(db, select(Location).where(Location.organization_id == org_id, Location.is_active.is_(True))),
        "equipment_total": _count(db, select(Equipment).where(Equipment.organization_id == org_id)),
        "requests_total": _count(db, requests_base),
        "requests_open": _count(db, requests_base.where(MR.status.in_(list(OPEN_STATES)))),
        "recent_audit": [
            {"id": i, "action": a, "detail": d, "created_at": c, "actor": n} for i, a, d, c, n in recent_audit
        ],
    }


@router.get("/summary")
def summary(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(P.REPORT_VIEW)),
):
    """Management report for one company. Viewing it changes nothing (UC-04)."""
    org_id = user.organization_id
    sla = sla_for(db, org_id)
    base = select(MR).where(MR.organization_id == org_id)
    if date_from:
        base = base.where(MR.created_at >= date_from)
    if date_to:
        base = base.where(MR.created_at <= end_of_day(date_to))

    by_status = _by_enum(db, base, MR.status, Status)
    sub = base.subquery()

    # Technician workload and repair time (FR-083).
    work_rows = db.execute(select(sub.c.technician_id, sub.c.status, sub.c.created_at, sub.c.resolved_at)).all()
    technicians = db.scalars(
        select(User)
        .join(RoleRecord, User.role_id == RoleRecord.id)
        .where(User.organization_id == org_id, RoleRecord.name == Role.TECHNICIAN)
        .order_by(User.name)
    )

    def hours(r) -> float:
        return (r.resolved_at - r.created_at).total_seconds() / 3600

    workload = []
    for tech in technicians:
        mine = [r for r in work_rows if r.technician_id == tech.id]
        done = [hours(r) for r in mine if r.resolved_at]
        if not mine and not tech.is_active:
            continue
        workload.append({
            "technician_id": tech.id,
            "technician": tech.name + ("" if tech.is_active else " (inactive)"),
            "open": sum(1 for r in mine if Status(r.status) in OPEN_STATES),
            "completed": sum(1 for r in mine if Status(r.status) in (Status.RESOLVED, Status.CLOSED)),
            "avg_hours": round(sum(done) / len(done), 1) if done else None,
        })
    all_done = [hours(r) for r in work_rows if r.resolved_at]

    # Equipment with repeated maintenance (FR-084): two or more linked requests.
    repeated = db.execute(
        select(Equipment.id, Equipment.asset_code, Equipment.name, func.count(sub.c.id).label("n"))
        .join(sub, sub.c.equipment_id == Equipment.id)
        .group_by(Equipment.id, Equipment.asset_code, Equipment.name)
        .having(func.count(sub.c.id) >= 2)
        .order_by(func.count(sub.c.id).desc())
    ).all()

    return {
        "total": sum(by_status.values()),
        "pending": sum(by_status[s.value] for s in (Status.NEW, Status.UNDER_REVIEW, Status.ASSIGNED, Status.ON_HOLD)),
        "in_progress": by_status[Status.IN_PROGRESS.value],
        "resolved": by_status[Status.RESOLVED.value] + by_status[Status.CLOSED.value],
        "rejected": by_status[Status.REJECTED.value],
        "overdue": _count(db, base.where(overdue_clause(sla))),
        "avg_completion_hours": round(sum(all_done) / len(all_done), 1) if all_done else None,
        "by_status": by_status,
        "by_priority": _by_enum(db, base, MR.priority, Priority),
        "by_category": _by_lookup(db, base, MR.category_id, Category, org_id),
        "by_location": _by_lookup(db, base, MR.location_id, Location, org_id),
        "technician_workload": workload,
        "repeated_equipment": [
            {"equipment_id": i, "asset_code": c, "name": n, "requests": k} for i, c, n, k in repeated
        ],
        "sla_hours": {p.value: h for p, h in sla.items()},
    }
