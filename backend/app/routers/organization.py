"""Company configuration for System Administrators, and the lookup lists everyone needs."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import can, get_current_user, require_permission
from ..enums import Permission as P
from ..models import Category, Location, Organization, SlaPolicy, User
from ..schemas import LookupIn, LookupOut, OrganizationSettings, OrganizationUpdate, SlaItem, SlaUpdate
from ..services.activity import record_audit
from ..services.org_setup import unique_join_code
from ..services.queries import in_company, sla_for

router = APIRouter(prefix="/organization", tags=["organization"])
admin_settings = require_permission(P.SETTINGS_MANAGE)


def settings_out(org: Organization) -> OrganizationSettings:
    out = OrganizationSettings.model_validate(org)
    out.ai_configured = settings.ai_configured
    out.ai_model = settings.gemini_model if settings.ai_configured else None
    return out


# ---------------------------------------------------------------- company ---
@router.get("", response_model=OrganizationSettings)
def get_organization(actor: User = Depends(admin_settings)):
    return settings_out(actor.organization)


@router.patch("", response_model=OrganizationSettings)
def update_organization(payload: OrganizationUpdate, db: Session = Depends(get_db), actor: User = Depends(admin_settings)):
    org = actor.organization
    data = payload.model_dump(exclude_none=True)
    if "name" in data and data["name"].lower() != org.name.lower():
        clash = db.scalar(
            select(Organization.id).where(func.lower(Organization.name) == data["name"].lower(), Organization.id != org.id)
        )
        if clash:
            raise HTTPException(status.HTTP_409_CONFLICT, "Another company already uses this name.")
    changed = [f"{k}={v}" for k, v in data.items() if getattr(org, k) != v]
    for key, value in data.items():
        setattr(org, key, value)
    if changed:
        record_audit(db, actor, "settings.updated", "Company settings: " + ", ".join(changed))
    db.commit()
    return settings_out(org)


@router.post("/join-code", response_model=OrganizationSettings)
def regenerate_join_code(db: Session = Depends(get_db), actor: User = Depends(admin_settings)):
    """Issue a new join code; the old one stops working immediately."""
    org = actor.organization
    org.join_code = unique_join_code(db)
    record_audit(db, actor, "settings.join_code", "Join code regenerated")
    db.commit()
    return settings_out(org)


# ------------------------------------------------- categories & locations ---
def _list(db: Session, model, actor: User, include_inactive: bool):
    query = select(model).where(model.organization_id == actor.organization_id)
    if not (include_inactive and (can(actor, P.SETTINGS_MANAGE) or can(actor, P.EQUIPMENT_MANAGE))):
        query = query.where(model.is_active.is_(True))
    return list(db.scalars(query.order_by(model.name)))


def _create(db: Session, model, label: str, payload: LookupIn, actor: User):
    if db.scalar(
        select(model.id).where(model.organization_id == actor.organization_id, func.lower(model.name) == payload.name.lower())
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, f"A {label} with this name already exists.")
    item = model(organization_id=actor.organization_id, name=payload.name, is_active=payload.is_active)
    db.add(item)
    record_audit(db, actor, f"settings.{label}", f"Added {label} '{payload.name}'")
    db.commit()
    return item


def _update(db: Session, model, label: str, item_id: int, payload: LookupIn, actor: User):
    item = in_company(db, model, item_id, actor.organization_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"That {label} was not found.")
    clash = db.scalar(
        select(model.id).where(
            model.organization_id == actor.organization_id,
            func.lower(model.name) == payload.name.lower(),
            model.id != item.id,
        )
    )
    if clash:
        raise HTTPException(status.HTTP_409_CONFLICT, f"A {label} with this name already exists.")
    detail = []
    if item.name != payload.name:
        detail.append(f"renamed '{item.name}' to '{payload.name}'")
    if item.is_active != payload.is_active:
        detail.append("reactivated" if payload.is_active else "retired")
    item.name, item.is_active = payload.name, payload.is_active
    if detail:
        record_audit(db, actor, f"settings.{label}", f"{label.capitalize()} " + ", ".join(detail))
    db.commit()
    return item


@router.get("/categories", response_model=list[LookupOut])
def list_categories(include_inactive: bool = False, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return _list(db, Category, actor, include_inactive)


@router.post("/categories", response_model=LookupOut, status_code=status.HTTP_201_CREATED)
def create_category(payload: LookupIn, db: Session = Depends(get_db), actor: User = Depends(admin_settings)):
    return _create(db, Category, "category", payload, actor)


@router.put("/categories/{item_id}", response_model=LookupOut)
def update_category(item_id: int, payload: LookupIn, db: Session = Depends(get_db), actor: User = Depends(admin_settings)):
    return _update(db, Category, "category", item_id, payload, actor)


@router.get("/locations", response_model=list[LookupOut])
def list_locations(include_inactive: bool = False, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return _list(db, Location, actor, include_inactive)


@router.post("/locations", response_model=LookupOut, status_code=status.HTTP_201_CREATED)
def create_location(payload: LookupIn, db: Session = Depends(get_db), actor: User = Depends(admin_settings)):
    return _create(db, Location, "location", payload, actor)


@router.put("/locations/{item_id}", response_model=LookupOut)
def update_location(item_id: int, payload: LookupIn, db: Session = Depends(get_db), actor: User = Depends(admin_settings)):
    return _update(db, Location, "location", item_id, payload, actor)


# ----------------------------------------------------------- service targets ---
@router.get("/sla", response_model=list[SlaItem])
def get_sla(db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    sla = sla_for(db, actor.organization_id)
    return [SlaItem(priority=p, target_hours=h) for p, h in sla.items()]


@router.put("/sla", response_model=list[SlaItem])
def update_sla(payload: SlaUpdate, db: Session = Depends(get_db), actor: User = Depends(admin_settings)):
    """Service target per priority. Used to decide when open work is overdue (BR-010)."""
    existing = {
        r.priority: r for r in db.scalars(select(SlaPolicy).where(SlaPolicy.organization_id == actor.organization_id))
    }
    changes = []
    for item in payload.items:
        row = existing.get(item.priority)
        if row is None:
            db.add(SlaPolicy(organization_id=actor.organization_id, priority=item.priority, target_hours=item.target_hours))
            changes.append(f"{item.priority.value} {item.target_hours} h")
        elif row.target_hours != item.target_hours:
            changes.append(f"{item.priority.value} {row.target_hours} h to {item.target_hours} h")
            row.target_hours = item.target_hours
    if changes:
        record_audit(db, actor, "settings.sla", "Service targets: " + ", ".join(changes))
    db.commit()
    return get_sla(db, actor)
