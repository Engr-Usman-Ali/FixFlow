"""Company creation and RBAC table sync."""
import re

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import settings
from ..enums import Permission, Priority, Role
from ..models import Category, Location, Organization, PermissionRecord, RolePermission, RoleRecord, SlaPolicy
from ..rbac import PERMISSION_DESCRIPTIONS, ROLE_DESCRIPTIONS, ROLE_PERMISSIONS
from ..security import new_join_code

# Starting lists for a new company. Administrators can rename, add or retire them.
DEFAULT_CATEGORIES = [
    "Electrical", "Plumbing", "HVAC", "Mechanical", "IT & Network",
    "Building & Facility", "Furniture & Fixtures", "Safety", "Other",
]
DEFAULT_LOCATIONS = ["Main building"]


def default_sla() -> dict[Priority, int]:
    return {
        Priority.CRITICAL: settings.default_sla_critical_hours,
        Priority.HIGH: settings.default_sla_high_hours,
        Priority.MEDIUM: settings.default_sla_medium_hours,
        Priority.LOW: settings.default_sla_low_hours,
    }


def sync_rbac(db: Session) -> None:
    """Write the RBAC matrix from rbac.py into the roles/permissions tables."""
    perms = {p.code: p for p in db.scalars(select(PermissionRecord))}
    for perm in Permission:
        record = perms.get(perm.value)
        if record is None:
            record = PermissionRecord(code=perm.value, description=PERMISSION_DESCRIPTIONS[perm])
            db.add(record)
            perms[perm.value] = record
        else:
            record.description = PERMISSION_DESCRIPTIONS[perm]

    roles = {r.name: r for r in db.scalars(select(RoleRecord))}
    for role in Role:
        record = roles.get(role)
        if record is None:
            record = RoleRecord(name=role, description=ROLE_DESCRIPTIONS[role])
            db.add(record)
            roles[role] = record
        else:
            record.description = ROLE_DESCRIPTIONS[role]
    db.flush()

    db.execute(delete(RolePermission))
    for role, granted in ROLE_PERMISSIONS.items():
        for perm in granted:
            db.add(RolePermission(role_id=roles[role].id, permission_id=perms[perm.value].id))
    db.commit()
    clear_role_cache()


# Role ids never change after sync, so they are cached per process.
_ROLE_IDS: dict[Role, int] = {}


def clear_role_cache() -> None:
    _ROLE_IDS.clear()


def role_id(db: Session, role: Role) -> int:
    if not _ROLE_IDS:
        _ROLE_IDS.update({r.name: r.id for r in db.scalars(select(RoleRecord))})
    return _ROLE_IDS[role]


def suggest_prefix(name: str) -> str:
    letters = re.sub(r"[^A-Za-z]", "", name).upper()
    return (letters[:4] or "REQ").ljust(2, "X")


def unique_join_code(db: Session) -> str:
    while True:
        code = new_join_code()
        if not db.scalar(select(Organization.id).where(Organization.join_code == code)):
            return code


def create_organization(db: Session, name: str, request_prefix: str | None = None) -> Organization:
    """Create a company with default categories, a location and service targets."""
    org = Organization(
        name=name.strip(),
        join_code=unique_join_code(db),
        request_prefix=(request_prefix or suggest_prefix(name)).upper(),
        allow_self_signup=True,
        ai_enabled=True,
    )
    db.add(org)
    db.flush()
    db.add_all(Category(organization_id=org.id, name=c) for c in DEFAULT_CATEGORIES)
    db.add_all(Location(organization_id=org.id, name=loc) for loc in DEFAULT_LOCATIONS)
    db.add_all(SlaPolicy(organization_id=org.id, priority=p, target_hours=h) for p, h in default_sla().items())
    db.flush()
    return org
