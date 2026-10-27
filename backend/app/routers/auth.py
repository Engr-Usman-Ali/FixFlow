"""Sign-up, sign-in, sign-out and profile (FR-001 to FR-006)."""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user, permissions_of
from ..enums import Role
from ..models import Organization, User, utcnow
from ..schemas import (
    JoinIn,
    LoginIn,
    PasswordChange,
    ProfileUpdate,
    RegisterOrganizationIn,
    SessionUser,
    TokenOut,
)
from ..security import burn_time, create_access_token, hash_password, needs_rehash, password_problem, verify_password
from ..services.activity import record_audit
from ..services.org_setup import create_organization, role_id

router = APIRouter(prefix="/auth", tags=["auth"])

# One message for every sign-in failure, so nobody can learn whether an
# account exists or is locked (FR-002).
SIGN_IN_FAILED = (
    "Incorrect email or password. After several failed attempts an account is locked "
    "for a few minutes."
)


# ---------------------------------------------------------------- helpers ---
def session_user(user: User) -> SessionUser:
    out = SessionUser.model_validate(user)
    out.permissions = sorted(p.value for p in permissions_of(user))
    return out


def token_response(user: User) -> TokenOut:
    token, expires = create_access_token(user.id, user.organization_id, user.token_version)
    return TokenOut(access_token=token, expires_at=expires, user=session_user(user))


def set_password(user: User, password: str) -> None:
    hashed = hash_password(password)
    user.password_hash = hashed.hash
    user.password_salt = hashed.salt
    user.password_iterations = hashed.iterations
    user.password_changed_at = utcnow()


def check_password_rules(password: str) -> None:
    problem = password_problem(password)
    if problem:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, problem)


def ensure_email_free(db: Session, email: str) -> None:
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")


def new_user(db: Session, org: Organization, name: str, email: str, password: str, role: Role) -> User:
    user = User(organization_id=org.id, role_id=role_id(db, role), name=name, email=email)
    set_password(user, password)
    db.add(user)
    db.flush()
    return user


# -------------------------------------------------------------- sign-up ---
@router.post("/register-organization", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register_organization(payload: RegisterOrganizationIn, db: Session = Depends(get_db)):
    """Create a new company. The person signing up becomes its System Administrator."""
    check_password_rules(payload.password)
    ensure_email_free(db, payload.email)
    if db.scalar(select(Organization.id).where(func.lower(Organization.name) == payload.organization_name.lower())):
        raise HTTPException(status.HTTP_409_CONFLICT, "A company with this name is already registered.")

    org = create_organization(db, payload.organization_name, payload.request_prefix)
    admin = new_user(db, org, payload.name, payload.email, payload.password, Role.ADMIN)
    record_audit(db, admin, "organization.created", f"Company '{org.name}' registered by {admin.name}")
    db.commit()
    return token_response(admin)


@router.post("/join", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def join_organization(payload: JoinIn, db: Session = Depends(get_db)):
    """Self sign-up into an existing company. New members always start as Employees."""
    org = db.scalar(select(Organization).where(Organization.join_code == payload.join_code))
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No company uses this join code. Check it with your administrator.")
    if not org.allow_self_signup:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "This company does not allow self sign-up. Ask your administrator to create your account.",
        )
    check_password_rules(payload.password)
    ensure_email_free(db, payload.email)

    user = new_user(db, org, payload.name, payload.email, payload.password, Role.EMPLOYEE)
    record_audit(db, user, "user.joined", f"{user.name} joined with the company code", target_user=user)
    db.commit()
    return token_response(user)


# -------------------------------------------------------------- sign-in ---
@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not user.is_active or user.is_locked:
        burn_time(payload.password)  # same timing as a real check
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, SIGN_IN_FAILED)

    if not verify_password(payload.password, user.password_hash, user.password_salt, user.password_iterations):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.login_max_attempts:
            user.locked_until = utcnow() + timedelta(minutes=settings.login_lockout_minutes)
            user.failed_login_attempts = 0
            record_audit(db, user, "user.locked", f"{user.name} locked after repeated failed sign-ins", target_user=user)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, SIGN_IN_FAILED)

    if needs_rehash(user.password_iterations):  # upgrade older hashes transparently
        set_password(user, payload.password)
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = utcnow()
    db.commit()
    return token_response(user)


@router.post("/logout")
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Ends the session: every token issued before now stops working (FR-005)."""
    user.token_version += 1
    db.commit()
    return {"ok": True}


# -------------------------------------------------------------- profile ---
@router.get("/me", response_model=SessionUser)
def me(user: User = Depends(get_current_user)):
    return session_user(user)


@router.patch("/me", response_model=SessionUser)
def update_profile(payload: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.name = payload.name
    db.commit()
    return session_user(user)


@router.post("/change-password", response_model=TokenOut)
def change_password(payload: PasswordChange, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(payload.current_password, user.password_hash, user.password_salt, user.password_iterations):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Your current password is not correct.")
    if payload.new_password == payload.current_password:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose a password different from the current one.")
    check_password_rules(payload.new_password)

    set_password(user, payload.new_password)
    user.token_version += 1  # other devices are signed out
    record_audit(db, user, "user.password_changed", f"{user.name} changed their password", target_user=user)
    db.commit()
    return token_response(user)  # this device stays signed in with a fresh token
