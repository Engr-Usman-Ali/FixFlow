"""User administration for System Administrators (FR-102), plus the technician list for managers."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_any_permission, require_permission
from ..enums import Permission as P
from ..enums import Role
from ..models import RoleRecord, User
from ..rbac import PERMISSION_DESCRIPTIONS, ROLE_DESCRIPTIONS, ROLE_PERMISSIONS
from ..schemas import PasswordReset, PermissionOut, RoleOut, UserBrief, UserCreate, UserOut, UserUpdate
from ..services.activity import record_audit
from ..services.org_setup import role_id
from ..services.queries import in_company
from .auth import check_password_rules, ensure_email_free, set_password

router = APIRouter(tags=["users"])
admin_only = require_permission(P.USER_MANAGE)


def _get_user(db: Session, user_id: int, actor: User) -> User:
    user = in_company(db, User, user_id, actor.organization_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    return user


def _active_admin_count(db: Session, organization_id: int) -> int:
    query = (
        select(func.count())
        .select_from(User)
        .join(RoleRecord, User.role_id == RoleRecord.id)
        .where(User.organization_id == organization_id, User.is_active.is_(True), RoleRecord.name == Role.ADMIN)
    )
    return db.scalar(query) or 0


# ------------------------------------------------------------------ users ---
@router.get("/users", response_model=list[UserOut])
def list_users(
    q: Optional[str] = None,
    role: Optional[Role] = None,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_only),
):
    query = select(User).where(User.organization_id == actor.organization_id)
    if q:
        term = f"%{q.strip()}%"
        query = query.where(or_(User.name.ilike(term), User.email.ilike(term)))
    if role:
        query = query.join(RoleRecord, User.role_id == RoleRecord.id).where(RoleRecord.name == role)
    return list(db.scalars(query.order_by(User.name)))


@router.get("/users/technicians", response_model=list[UserBrief])
def list_technicians(
    db: Session = Depends(get_db),
    actor: User = Depends(require_any_permission(P.REQUEST_ASSIGN, P.REQUEST_VIEW_ALL)),
):
    """Eligible assignees: active technicians of the same company (FR-022)."""
    query = (
        select(User)
        .join(RoleRecord, User.role_id == RoleRecord.id)
        .where(
            User.organization_id == actor.organization_id,
            User.is_active.is_(True),
            RoleRecord.name == Role.TECHNICIAN,
        )
        .order_by(User.name)
    )
    return list(db.scalars(query))


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db), actor: User = Depends(admin_only)):
    check_password_rules(payload.password)
    ensure_email_free(db, payload.email)
    user = User(
        organization_id=actor.organization_id,
        role_id=role_id(db, payload.role),
        name=payload.name,
        email=payload.email,
    )
    set_password(user, payload.password)
    db.add(user)
    db.flush()
    record_audit(db, actor, "user.created", f"Created {user.name} ({user.email}) as {payload.role.value}", target_user=user)
    db.commit()
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), actor: User = Depends(admin_only)):
    user = _get_user(db, user_id, actor)
    changes: list[str] = []

    if user.id == actor.id and (
        (payload.role is not None and payload.role != user.role) or payload.is_active is False
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "You cannot change your own role or deactivate yourself.")

    losing_admin = user.role == Role.ADMIN and user.is_active and (
        (payload.role is not None and payload.role != Role.ADMIN) or payload.is_active is False
    )
    if losing_admin and _active_admin_count(db, actor.organization_id) <= 1:
        raise HTTPException(status.HTTP_409_CONFLICT, "The company must keep at least one active System Administrator.")

    if payload.name is not None and payload.name != user.name:
        changes.append(f"name '{user.name}' to '{payload.name}'")
        user.name = payload.name
    if payload.role is not None and payload.role != user.role:
        changes.append(f"role {user.role.value} to {payload.role.value}")
        user.role_id = role_id(db, payload.role)
        db.flush()
        db.refresh(user)
        user.token_version += 1  # new permissions take effect at next sign-in
    if payload.is_active is not None and payload.is_active != user.is_active:
        changes.append("reactivated" if payload.is_active else "deactivated")
        user.is_active = payload.is_active
        user.token_version += 1

    if changes:
        record_audit(db, actor, "user.updated", f"{user.name}: " + ", ".join(changes), target_user=user)
        db.commit()
    return user


@router.post("/users/{user_id}/reset-password", response_model=UserOut)
def reset_password(user_id: int, payload: PasswordReset, db: Session = Depends(get_db), actor: User = Depends(admin_only)):
    user = _get_user(db, user_id, actor)
    check_password_rules(payload.new_password)
    set_password(user, payload.new_password)
    user.token_version += 1
    user.locked_until = None
    user.failed_login_attempts = 0
    record_audit(db, actor, "user.password_reset", f"Password reset for {user.name}", target_user=user)
    db.commit()
    return user


@router.post("/users/{user_id}/unlock", response_model=UserOut)
def unlock_user(user_id: int, db: Session = Depends(get_db), actor: User = Depends(admin_only)):
    user = _get_user(db, user_id, actor)
    user.locked_until = None
    user.failed_login_attempts = 0
    record_audit(db, actor, "user.unlocked", f"Unlocked {user.name}", target_user=user)
    db.commit()
    return user


# ------------------------------------------------------------------ roles ---
@router.get("/roles", response_model=list[RoleOut])
def list_roles(db: Session = Depends(get_db), actor: User = Depends(admin_only)):
    """The RBAC matrix, with how many people in this company hold each role."""
    counts = dict(
        db.execute(
            select(RoleRecord.name, func.count(User.id))
            .join(User, User.role_id == RoleRecord.id)
            .where(User.organization_id == actor.organization_id, User.is_active.is_(True))
            .group_by(RoleRecord.name)
        ).all()
    )
    return [
        RoleOut(
            name=role,
            description=ROLE_DESCRIPTIONS[role],
            permissions=sorted(p.value for p in ROLE_PERMISSIONS[role]),
            user_count=counts.get(role, 0),
        )
        for role in Role
    ]


@router.get("/roles/permissions", response_model=list[PermissionOut])
def list_permissions(_: User = Depends(admin_only)):
    return [PermissionOut(code=p.value, description=d) for p, d in PERMISSION_DESCRIPTIONS.items()]
