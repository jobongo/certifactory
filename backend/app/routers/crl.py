from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import User, UserRole
from app.schemas.crl import CRLResponse
from app.services.crl_service import CRLService

router = APIRouter(prefix="/api/v1/cas", tags=["crl"])
crl_service = CRLService()


@router.post("/{ca_id}/crl/generate", response_model=CRLResponse)
def generate_crl(
    ca_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator)),
):
    try:
        return crl_service.generate_crl(db, ca_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{ca_id}/crl")
def download_crl(
    ca_id: str,
    db: Session = Depends(get_db),
):
    crl = crl_service.get_latest_crl(db, ca_id)
    if not crl:
        raise HTTPException(status_code=404, detail="No CRL found for this CA")
    return Response(
        content=crl.crl_pem.encode(),
        media_type="application/pkix-crl",
        headers={"Content-Disposition": "attachment; filename=crl.pem"},
    )
