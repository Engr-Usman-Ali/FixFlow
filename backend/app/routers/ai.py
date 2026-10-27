"""Optional Gemini suggestions. Failures never block the core workflow (FR-093)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import can, get_current_user, require_permission
from ..enums import Permission as P
from ..models import Category, User
from ..schemas import SuggestIn, SuggestOut
from ..services import gemini

router = APIRouter(prefix="/ai", tags=["ai"])


def ai_enabled_for(user: User) -> bool:
    return settings.ai_configured and user.organization.ai_enabled


@router.get("/status")
def ai_status(user: User = Depends(get_current_user)):
    enabled = ai_enabled_for(user) and can(user, P.AI_SUGGEST)
    return {"enabled": enabled, "model": settings.gemini_model if enabled else None}


@router.post("/suggest", response_model=SuggestOut)
def suggest(payload: SuggestIn, db: Session = Depends(get_db), user: User = Depends(require_permission(P.AI_SUGGEST))):
    if not ai_enabled_for(user):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "AI suggestions are switched off. You can continue without them.",
        )
    categories = list(
        db.scalars(
            select(Category).where(Category.organization_id == user.organization_id, Category.is_active.is_(True))
        )
    )
    try:
        return SuggestOut(**gemini.suggest(payload.title, payload.description, categories))
    except gemini.AIUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"{exc} You can continue without AI suggestions.")
