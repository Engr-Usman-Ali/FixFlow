"""Maintenance requests: create, list, review, assign, work and close.

Sections: helpers -> list/create/detail -> manager actions -> status -> work logs and comments.
Every endpoint commits once at the end, so partial updates are never saved (NFR-REL-003).
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import can, get_current_user, permissions_of, require_permission
from ..enums import Permission as P
from ..enums import Priority, Role, Status
from ..models import (
    Assignment,
    Category,
    Comment,
    Equipment,
    Location,
    MaintenanceRequest as MR,
    Organization,
    User,
    WorkLog,
)
from ..schemas import (
    AssignIn,
    CommentIn,
    CommentOut,
    Page,
    PriorityIn,
    RequestCreate,
    RequestDetail,
    RequestOut,
    StatusIn,
    WorkLogIn,
    WorkLogOut,
)
from ..services.activity import notify, record_audit, record_status
from ..services.queries import (
    can_view,
    end_of_day,
    in_company,
    overdue_clause,
    sla_for,
    users_with,
    visible_requests,
)
from ..services.serializers import request_detail, request_out
from ..workflow import (
    ASSIGNABLE_STATES,
    FINISHED_STATES,
    NEEDS_TECHNICIAN,
    PRIORITY_RANK,
    WORK_LOG_STATES,
    can_transition,
    completion_ok,
    ends_assignment,
    is_known_transition,
    requires_reason,
)

router = APIRouter(prefix="/requests", tags=["requests"])


# ---------------------------------------------------------------- helpers ---
def get_visible_request(db: Session, request_id: int, user: User) -> MR:
    """Unknown, other-company and forbidden ids all look the same (BR-008)."""
    req = db.get(MR, request_id)
    if req is None or not can_view(user, req):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found.")
    return req


def detail_response(db: Session, req: MR, user: User) -> RequestDetail:
    db.refresh(req)  # reload relationships changed during this call
    return request_detail(req, user, sla_for(db, user.organization_id))


def stakeholders(req: MR) -> list[Optional[User]]:
    return [req.creator, req.technician]


def end_open_assignment(req: MR, when: datetime, reason: Optional[str] = None) -> None:
    for open_assignment in (a for a in req.assignments if a.ended_at is None):
        open_assignment.ended_at = when
        if reason and not open_assignment.reason:
            open_assignment.reason = reason


def next_request_number(db: Session, organization_id: int) -> int:
    # Lock the company row so two people submitting at once never get the same number.
    db.execute(select(Organization.id).where(Organization.id == organization_id).with_for_update())
    current = db.scalar(select(func.max(MR.request_number)).where(MR.organization_id == organization_id))
    return (current or 0) + 1


# ------------------------------------------------------------- list/create ---
@router.get("", response_model=Page[RequestOut])
def list_requests(
    q: Optional[str] = Query(default=None, max_length=200),
    status_filter: Optional[list[Status]] = Query(default=None, alias="status"),
    category_id: Optional[int] = None,
    priority: Optional[Priority] = None,
    location_id: Optional[int] = None,
    technician_id: Optional[int] = None,
    equipment_id: Optional[int] = None,
    overdue: Optional[bool] = None,
    unassigned: Optional[bool] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    sort: str = Query(default="created_at", pattern="^(created_at|updated_at|priority|status|title|request_number)$"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Search, filter, sort and page. Always limited to what the user may see (FR-070 to FR-073)."""
    query = visible_requests(user)
    sla = sla_for(db, user.organization_id)

    if q and q.strip():
        term = q.strip()
        digits = term.upper().split("-")[-1].lstrip("0")
        conditions = [MR.title.ilike(f"%{term}%"), MR.description.ilike(f"%{term}%")]
        if digits.isdigit():
            conditions.append(MR.request_number == int(digits))
        query = query.where(or_(*conditions))
    if status_filter:
        query = query.where(MR.status.in_(status_filter))
    if category_id:
        query = query.where(MR.category_id == category_id)
    if priority:
        query = query.where(MR.priority == priority)
    if location_id:
        query = query.where(MR.location_id == location_id)
    if technician_id and can(user, P.REQUEST_VIEW_ALL):
        query = query.where(MR.technician_id == technician_id)
    if equipment_id:
        query = query.where(MR.equipment_id == equipment_id)
    if unassigned:
        query = query.where(MR.technician_id.is_(None))
    if overdue:
        query = query.where(overdue_clause(sla))
    if date_from:
        query = query.where(MR.created_at >= date_from)
    if date_to:
        query = query.where(MR.created_at <= end_of_day(date_to))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    if sort == "priority":  # rank, so "desc" means most urgent first
        sort_column = case(*[(MR.priority == p, r) for p, r in PRIORITY_RANK.items()], else_=0)
    else:
        sort_column = getattr(MR, sort)
    ordering = sort_column.desc() if order == "desc" else sort_column.asc()

    rows = db.scalars(
        query.options(
            joinedload(MR.creator),
            joinedload(MR.technician),
            joinedload(MR.equipment),
            joinedload(MR.category),
            joinedload(MR.location),
        )
        .order_by(ordering, MR.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).unique()
    return Page[RequestOut](items=[request_out(r, sla) for r in rows], total=total, page=page, page_size=page_size)


@router.post("", response_model=RequestOut, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: RequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(P.REQUEST_CREATE)),
):
    """FR-010 to FR-014: validate, store with a unique id and initial status, notify reviewers."""
    org_id = user.organization_id
    category = in_company(db, Category, payload.category_id, org_id)
    if category is None or not category.is_active:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose a valid category.")
    location = in_company(db, Location, payload.location_id, org_id)
    if location is None or not location.is_active:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose a valid location.")
    if payload.equipment_id is not None:
        equipment = in_company(db, Equipment, payload.equipment_id, org_id)
        if equipment is None or not equipment.is_active:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "The selected equipment does not exist.")

    req = MR(
        organization_id=org_id,
        request_number=next_request_number(db, org_id),
        title=payload.title,
        description=payload.description,
        category_id=category.id,
        location_id=location.id,
        location_detail=payload.location_detail or None,
        priority=payload.priority,
        equipment_id=payload.equipment_id,
        creator_id=user.id,
        status=Status.NEW,
        priority_confirmed=False,
    )
    db.add(req)
    db.flush()  # gives req.id for history and notifications
    db.refresh(req)
    record_status(db, req, None, Status.NEW, user, "Request submitted")
    record_audit(db, user, "request.created", f"Created {req.ref}", request=req)
    if payload.ai_suggestion_used:
        record_audit(db, user, "ai.applied", "Category/priority taken from an AI suggestion and reviewed by the submitter", request=req)
    notify(db, req, "created", f"New request: {req.title}", users_with(db, org_id, P.REQUEST_REVIEW), user)
    db.commit()
    return request_out(req, sla_for(db, org_id))


@router.get("/{request_id}", response_model=RequestDetail)
def get_request(request_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return detail_response(db, get_visible_request(db, request_id, user), user)


# -------------------------------------------------------- manager actions ---
@router.post("/{request_id}/priority", response_model=RequestDetail)
def confirm_priority(
    request_id: int,
    payload: PriorityIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(P.REQUEST_REVIEW)),
):
    """FR-021: confirm or change priority."""
    req = get_visible_request(db, request_id, user)
    if req.status in FINISHED_STATES:
        raise HTTPException(status.HTTP_409_CONFLICT, f"The priority of a {req.status.value} request cannot change.")
    old = req.priority
    req.priority = payload.priority
    req.priority_confirmed = True
    text = f"Priority confirmed as {old.value}" if old == payload.priority else f"Priority changed: {old.value} to {payload.priority.value}"
    record_audit(db, user, "priority", text, request=req)
    db.commit()
    return detail_response(db, req, user)


@router.post("/{request_id}/assign", response_model=RequestDetail)
def assign_technician(
    request_id: int,
    payload: AssignIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(P.REQUEST_ASSIGN)),
):
    """FR-022, FR-023, FR-025: assign or reassign, keeping the full assignment history."""
    req = get_visible_request(db, request_id, user)
    if req.status not in ASSIGNABLE_STATES:
        raise HTTPException(status.HTTP_409_CONFLICT, f"A {req.status.value} request cannot be assigned.")

    tech = in_company(db, User, payload.technician_id, user.organization_id)
    if tech is None or tech.role != Role.TECHNICIAN or not tech.is_active:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose an active technician from your company.")
    if req.technician_id == tech.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "This technician is already assigned.")

    previous = req.technician
    now = datetime.now(timezone.utc)
    end_open_assignment(req, now)
    db.add(Assignment(request_id=req.id, technician_id=tech.id, assigned_by_id=user.id, reason=payload.note or None))
    req.technician_id = tech.id

    if payload.priority:
        if payload.priority != req.priority:
            record_audit(db, user, "priority", f"Priority changed: {req.priority.value} to {payload.priority.value}", request=req)
            req.priority = payload.priority
        req.priority_confirmed = True

    verb = "Reassigned" if previous else "Assigned"
    note = f" ({payload.note})" if payload.note else ""
    record_audit(db, user, "assignment", f"{verb} to {tech.name}{note}", request=req)

    if req.status in (Status.NEW, Status.UNDER_REVIEW, Status.ON_HOLD):
        record_status(db, req, req.status, Status.ASSIGNED, user, f"{verb} to {tech.name}")
        req.status = Status.ASSIGNED

    db.flush()
    db.refresh(req)
    notify(db, req, "assigned", f"{verb} to {tech.name}: {req.title}", [tech, req.creator], user)
    if previous:
        notify(db, req, "reassigned", f"You were taken off: {req.title}", [previous], user)
    db.commit()
    return detail_response(db, req, user)


# ----------------------------------------------------------------- status ---
@router.post("/{request_id}/status", response_model=RequestDetail)
def change_status(
    request_id: int, payload: StatusIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Every status move goes through the transition table in workflow.py (FR-033, FR-040 to FR-043)."""
    req = get_visible_request(db, request_id, user)
    old, new = req.status, payload.status
    perms = permissions_of(user)

    if not is_known_transition(old, new):
        raise HTTPException(status.HTTP_409_CONFLICT, f"A request cannot move from {old.value} to {new.value}.")
    if not can_transition(old, new, perms, is_assignee=req.technician_id == user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission to make this change.")

    reason = (payload.reason or "").strip()
    if requires_reason(old, new) and len(reason) < 3:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Give a reason for this change.")
    if new in NEEDS_TECHNICIAN and req.technician_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Assign a technician first.")

    now = datetime.now(timezone.utc)
    if new == Status.RESOLVED:  # BR-004
        if not completion_ok(payload.completion_details):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Add completion details (at least 10 characters) describing what was fixed before resolving.",
            )
        req.completion_details = payload.completion_details.strip()  # type: ignore[union-attr]
        req.resolved_at = now
    if new == Status.CLOSED:  # FR-041
        req.closed_at = now
        req.closed_by_id = user.id
    if old in (Status.CLOSED, Status.REJECTED) or (old == Status.RESOLVED and new == Status.IN_PROGRESS):
        # Reopened or sent back: clear completion markers; history keeps the past.
        req.closed_at = None
        req.closed_by_id = None
        req.resolved_at = None

    previous_tech = req.technician
    if ends_assignment(new) and req.technician_id is not None:
        end_open_assignment(req, now, reason or "Returned to review")
        record_audit(db, user, "assignment", f"{previous_tech.name} unassigned (returned to review)", request=req)
        req.technician_id = None

    req.status = new
    record_status(db, req, old, new, user, reason or None)
    db.flush()
    db.refresh(req)

    recipients = stakeholders(req) + [previous_tech]
    if new == Status.RESOLVED:
        recipients += users_with(db, req.organization_id, P.REQUEST_CLOSE)
        message = f"Work completed, ready for review: {req.title}"
    else:
        message = f"Status changed to {new.value}: {req.title}" + (f" (reason: {reason})" if reason else "")
    notify(db, req, "status", message, recipients, user)
    db.commit()
    return detail_response(db, req, user)


# ----------------------------------------------- work logs and comments ---
@router.post("/{request_id}/work-logs", response_model=WorkLogOut, status_code=status.HTTP_201_CREATED)
def add_work_log(
    request_id: int,
    payload: WorkLogIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(P.REQUEST_WORK)),
):
    """FR-031, FR-032: dated diagnosis / action / materials entries. Append-only (FR-035)."""
    req = get_visible_request(db, request_id, user)
    if req.technician_id != user.id and not can(user, P.REQUEST_WORK_ANY):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the assigned technician can record work on this request.")
    if req.status not in WORK_LOG_STATES:
        raise HTTPException(status.HTTP_409_CONFLICT, "Work can be logged only while a request is assigned, in progress or on hold.")
    if not (payload.diagnosis or "").strip() and not (payload.action_taken or "").strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Describe the diagnosis or the action taken.")

    log = WorkLog(
        request_id=req.id,
        author_id=user.id,
        diagnosis=payload.diagnosis or None,
        action_taken=payload.action_taken or None,
        materials_used=payload.materials_used or None,
    )
    db.add(log)
    db.flush()
    notify(db, req, "work_log", f"{user.name} recorded work: {req.title}", [req.creator], user)
    db.commit()
    db.refresh(log)
    return WorkLogOut.model_validate(log)


@router.post("/{request_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(
    request_id: int,
    payload: CommentIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(P.REQUEST_COMMENT)),
):
    """FR-060, FR-061: comments record author and time."""
    req = get_visible_request(db, request_id, user)
    comment = Comment(request_id=req.id, author_id=user.id, body=payload.body)
    db.add(comment)
    db.flush()
    recipients = stakeholders(req) + users_with(db, req.organization_id, P.REQUEST_VIEW_ALL)
    notify(db, req, "comment", f"{user.name} commented: {req.title}", recipients, user)
    db.commit()
    db.refresh(comment)
    return CommentOut.model_validate(comment)
