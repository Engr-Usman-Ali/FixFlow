"""Equipment register (FR-050 to FR-054)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import require_permission
from ..enums import Permission as P
from ..models import Category, Equipment, Location, MaintenanceRequest, User
from ..schemas import EquipmentIn, EquipmentOut, RequestOut
from ..services.activity import record_audit
from ..services.queries import in_company, sla_for, visible_requests
from ..services.serializers import request_out

router = APIRouter(prefix="/equipment", tags=["equipment"])
can_read = require_permission(P.EQUIPMENT_VIEW)
can_manage = require_permission(P.EQUIPMENT_MANAGE)


def _out(db: Session, item: Equipment) -> EquipmentOut:
    out = EquipmentOut.model_validate(item)
    out.request_count = db.scalar(
        select(func.count()).where(MaintenanceRequest.equipment_id == item.id)
    ) or 0
    return out


def _validate_links(db: Session, payload: EquipmentIn, org_id: int) -> None:
    if in_company(db, Category, payload.category_id, org_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose a valid category.")
    if in_company(db, Location, payload.location_id, org_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose a valid location.")


def _code_taken(db: Session, org_id: int, code: str, exclude_id: Optional[int] = None) -> bool:
    query = select(Equipment.id).where(Equipment.organization_id == org_id, Equipment.asset_code == code)
    if exclude_id:
        query = query.where(Equipment.id != exclude_id)
    return db.scalar(query) is not None


@router.get("", response_model=list[EquipmentOut])
def list_equipment(
    q: Optional[str] = Query(default=None, max_length=100),
    active_only: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(can_read),
):
    counts = (
        select(MaintenanceRequest.equipment_id, func.count().label("n"))
        .where(MaintenanceRequest.organization_id == user.organization_id, MaintenanceRequest.equipment_id.is_not(None))
        .group_by(MaintenanceRequest.equipment_id)
        .subquery()
    )
    query = (
        select(Equipment, func.coalesce(counts.c.n, 0))
        .outerjoin(counts, counts.c.equipment_id == Equipment.id)
        .where(Equipment.organization_id == user.organization_id)
        .options(joinedload(Equipment.category), joinedload(Equipment.location))
    )
    if active_only:
        query = query.where(Equipment.is_active.is_(True))
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.where(or_(Equipment.asset_code.ilike(term), Equipment.name.ilike(term)))
    result = []
    for item, n in db.execute(query.order_by(Equipment.asset_code)).unique():
        out = EquipmentOut.model_validate(item)
        out.request_count = n
        result.append(out)
    return result


@router.get("/{equipment_id}", response_model=EquipmentOut)
def get_equipment(equipment_id: int, db: Session = Depends(get_db), user: User = Depends(can_read)):
    item = in_company(db, Equipment, equipment_id, user.organization_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipment not found.")
    return _out(db, item)


@router.post("", response_model=EquipmentOut, status_code=status.HTTP_201_CREATED)
def create_equipment(payload: EquipmentIn, db: Session = Depends(get_db), user: User = Depends(can_manage)):
    _validate_links(db, payload, user.organization_id)
    if _code_taken(db, user.organization_id, payload.asset_code):
        raise HTTPException(status.HTTP_409_CONFLICT, "This asset code is already in use.")
    item = Equipment(organization_id=user.organization_id, **payload.model_dump())
    db.add(item)
    db.flush()
    record_audit(db, user, "equipment.created", f"Added equipment {item.asset_code} · {item.name}")
    db.commit()
    db.refresh(item)
    return _out(db, item)


@router.put("/{equipment_id}", response_model=EquipmentOut)
def update_equipment(equipment_id: int, payload: EquipmentIn, db: Session = Depends(get_db), user: User = Depends(can_manage)):
    item = in_company(db, Equipment, equipment_id, user.organization_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipment not found.")
    _validate_links(db, payload, user.organization_id)
    if _code_taken(db, user.organization_id, payload.asset_code, exclude_id=item.id):
        raise HTTPException(status.HTTP_409_CONFLICT, "This asset code is already in use.")
    for field, value in payload.model_dump().items():
        setattr(item, field, value)
    record_audit(db, user, "equipment.updated", f"Updated equipment {item.asset_code} · {item.name}")
    db.commit()
    db.refresh(item)
    return _out(db, item)


@router.get("/{equipment_id}/history", response_model=list[RequestOut])
def equipment_history(equipment_id: int, db: Session = Depends(get_db), user: User = Depends(can_read)):
    """FR-053: maintenance history, filtered to the requests this user may see."""
    if in_company(db, Equipment, equipment_id, user.organization_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipment not found.")
    query = (
        visible_requests(user)
        .where(MaintenanceRequest.equipment_id == equipment_id)
        .order_by(MaintenanceRequest.created_at.desc())
        .limit(200)
    )
    sla = sla_for(db, user.organization_id)
    return [request_out(r, sla) for r in db.scalars(query)]
