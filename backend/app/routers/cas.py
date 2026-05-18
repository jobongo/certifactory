from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import CAStatus, CertificateAuthority, User, UserRole
from app.schemas.ca import CACreate, CAListResponse, CAResponse, CATreeNode, CAUpdate
from app.services.ca_service import CAService
from app.services.import_service import ImportService

router = APIRouter(prefix="/api/v1/cas", tags=["certificate-authorities"])
ca_service = CAService()
import_service = ImportService()


@router.get("", response_model=CAListResponse)
def list_cas(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator, UserRole.auditor)),
):
    total = db.query(CertificateAuthority).count()
    items = db.query(CertificateAuthority).offset((page - 1) * per_page).limit(per_page).all()
    return CAListResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/tree", response_model=list[CATreeNode])
def get_ca_tree(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator, UserRole.auditor)),
):
    return ca_service.get_ca_tree(db)


@router.post("", response_model=CAResponse, status_code=status.HTTP_201_CREATED)
def create_root_ca(
    body: CACreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator)),
):
    data = body.model_dump()
    data["subject"] = body.subject.model_dump(exclude_none=True)
    ca = ca_service.create_root_ca(db, current_user.id, data)
    return ca


@router.post("/import", response_model=CAResponse, status_code=status.HTTP_201_CREATED)
async def import_ca(
    name: str = Form(...),
    cert_file: UploadFile | None = File(None),
    key_file: UploadFile | None = File(None),
    pkcs12_file: UploadFile | None = File(None),
    passphrase: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator)),
):
    cert_data = await cert_file.read() if cert_file else None
    key_data = await key_file.read() if key_file else None
    pkcs12_data = await pkcs12_file.read() if pkcs12_file else None
    if not cert_data and not pkcs12_data:
        raise HTTPException(status_code=400, detail="Provide either cert_file or pkcs12_file")
    try:
        ca, parent_detected = import_service.import_ca(db, current_user.id, name, cert_data, key_data, pkcs12_data, passphrase)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ca


@router.get("/{ca_id}", response_model=CAResponse)
def get_ca(
    ca_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator, UserRole.auditor)),
):
    ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == ca_id).first()
    if not ca:
        raise HTTPException(status_code=404, detail="CA not found")
    return ca


@router.put("/{ca_id}", response_model=CAResponse)
def update_ca(
    ca_id: str,
    body: CAUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator)),
):
    ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == ca_id).first()
    if not ca:
        raise HTTPException(status_code=404, detail="CA not found")
    update_data = body.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(ca, key, value)
    db.commit()
    db.refresh(ca)
    return ca


@router.post("/{ca_id}/intermediate", response_model=CAResponse, status_code=status.HTTP_201_CREATED)
def create_intermediate_ca(
    ca_id: str,
    body: CACreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator)),
):
    data = body.model_dump()
    data["subject"] = body.subject.model_dump(exclude_none=True)
    try:
        ca = ca_service.create_intermediate_ca(db, current_user.id, ca_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ca


@router.get("/{ca_id}/chain")
def get_ca_chain(
    ca_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.operator, UserRole.auditor)),
):
    chain = ca_service.get_chain(db, ca_id)
    if not chain:
        raise HTTPException(status_code=404, detail="CA not found")
    return {"chain": chain}


@router.delete("/{ca_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ca(
    ca_id: str,
    force: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    try:
        ca_service.delete_ca(db, current_user.id, ca_id, force=force)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{ca_id}/disable", response_model=CAResponse)
def disable_ca(
    ca_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == ca_id).first()
    if not ca:
        raise HTTPException(status_code=404, detail="CA not found")
    ca.status = CAStatus.disabled
    db.commit()
    db.refresh(ca)
    return ca


@router.post("/{ca_id}/enable", response_model=CAResponse)
def enable_ca(
    ca_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == ca_id).first()
    if not ca:
        raise HTTPException(status_code=404, detail="CA not found")
    ca.status = CAStatus.active
    db.commit()
    db.refresh(ca)
    return ca
