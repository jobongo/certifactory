from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import User, UserRole
from app.schemas.settings import SettingsDefinitionsResponse, SettingsUpdate
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])
settings_service = SettingsService()


@router.get("", response_model=SettingsDefinitionsResponse)
def get_settings(db: Session = Depends(get_db), current_user: User = Depends(require_role(UserRole.admin))):
    return SettingsDefinitionsResponse(
        definitions=settings_service.get_definitions(),
        values=settings_service.get_all(db),
    )


@router.put("")
def update_settings(body: SettingsUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_role(UserRole.admin))):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No settings to update")
    try:
        values = settings_service.update(db, updates)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"values": values}
