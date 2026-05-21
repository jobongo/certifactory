from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_role
from app.models import CertificateAuthority, CertificateTemplate, User, UserRole
from app.schemas.template import TemplateCreate, TemplateResponse, TemplateUpdate

router = APIRouter(prefix="/api/v1/cas", tags=["templates"])


@router.get("/{ca_id}/templates", response_model=list[TemplateResponse])
def list_templates(
    ca_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(CertificateTemplate).filter(CertificateTemplate.ca_id == ca_id).order_by(CertificateTemplate.name).all()


@router.post("/{ca_id}/templates", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    ca_id: str,
    body: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == ca_id).first()
    if not ca:
        raise HTTPException(status_code=404, detail="CA not found")
    template = CertificateTemplate(ca_id=ca_id, **body.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.put("/{ca_id}/templates/{template_id}", response_model=TemplateResponse)
def update_template(
    ca_id: str,
    template_id: str,
    body: TemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    template = db.query(CertificateTemplate).filter(
        CertificateTemplate.id == template_id, CertificateTemplate.ca_id == ca_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(template, key, value)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{ca_id}/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    ca_id: str,
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    template = db.query(CertificateTemplate).filter(
        CertificateTemplate.id == template_id, CertificateTemplate.ca_id == ca_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(template)
    db.commit()
