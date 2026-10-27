"""FastAPI dependencies: the signed-in user and permission checks (FR-004).

Every protected endpoint depends on one of these, so authorization is enforced
by the API whatever the browser shows or hides.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .enums import Permission
from .models import User
from .rbac import permissions_for
from .security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)

NOT_SIGNED_IN = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Your session has ended. Please sign in again.",
    headers={"WWW-Authenticate": "Bearer"},
)
FORBIDDEN = HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission to do this.")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise NOT_SIGNED_IN
    claims = decode_token(credentials.credentials)
    if claims is None:
        raise NOT_SIGNED_IN
    user = db.get(User, claims.user_id)
    if (
        user is None
        or not user.is_active
        or user.organization_id != claims.organization_id
        or user.token_version != claims.token_version  # signed out or access changed
    ):
        raise NOT_SIGNED_IN
    return user


def permissions_of(user: User) -> frozenset[Permission]:
    return permissions_for(user.role)


def can(user: User, permission: Permission) -> bool:
    return permission in permissions_of(user)


def require_permission(*needed: Permission):
    """Allow the call only if the user holds every listed permission."""

    def checker(user: User = Depends(get_current_user)) -> User:
        held = permissions_of(user)
        if not all(p in held for p in needed):
            raise FORBIDDEN
        return user

    return checker


def require_any_permission(*options: Permission):
    """Allow the call if the user holds at least one listed permission."""

    def checker(user: User = Depends(get_current_user)) -> User:
        held = permissions_of(user)
        if not any(p in held for p in options):
            raise FORBIDDEN
        return user

    return checker
