import base64
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import CAStatus, Certificate, CertificateAuthority, CertificateStatus, User, UserRole
from app.models.api_token import ApiToken
from app.services.ca_service import CAService
from app.services.certificate_service import CertificateService
from app.services.crl_service import CRLService

ca_service = CAService()
cert_service = CertificateService()
crl_service = CRLService()


def resolve_user(token: str | None, db: Session) -> User:
    if not token or not token.startswith("cf_"):
        raise ValueError("API token required (must start with cf_)")
    token_hash = ApiToken.hash_token(token)
    api_token = db.query(ApiToken).filter(ApiToken.token_hash == token_hash, ApiToken.is_active == True).first()
    if not api_token:
        raise ValueError("Invalid or revoked API token")
    user = db.query(User).filter(User.id == api_token.user_id).first()
    if not user or not user.is_active:
        raise ValueError("User not found or inactive")
    api_token.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return user


def _check_role(user: User, *allowed: UserRole):
    if user.role not in allowed:
        raise ValueError(f"Insufficient permissions. Required: {', '.join(r.value for r in allowed)}")


def _ca_to_dict(ca: CertificateAuthority) -> dict:
    return {
        "id": ca.id, "name": ca.name, "type": ca.type.value, "status": ca.status.value,
        "subject_dn": ca.subject_dn, "serial_number": ca.serial_number,
        "key_algorithm": ca.key_algorithm.value, "key_size": ca.key_size,
        "not_before": ca.not_before.isoformat() if ca.not_before else None,
        "not_after": ca.not_after.isoformat() if ca.not_after else None,
        "auto_approve": ca.auto_approve,
        "description": ca.description,
    }


def _cert_to_dict(cert: Certificate) -> dict:
    return {
        "id": cert.id, "ca_id": cert.ca_id, "status": cert.status.value,
        "type": cert.type.value, "subject_dn": cert.subject_dn,
        "serial_number": cert.serial_number, "san": cert.san,
        "key_algorithm": cert.key_algorithm.value, "key_size": cert.key_size,
        "not_before": cert.not_before.isoformat() if cert.not_before else None,
        "not_after": cert.not_after.isoformat() if cert.not_after else None,
        "key_usage": cert.key_usage, "extended_key_usage": cert.extended_key_usage,
        "has_private_key": cert.has_private_key,
        "revocation_date": cert.revocation_date.isoformat() if cert.revocation_date else None,
        "revocation_reason": cert.revocation_reason.value if cert.revocation_reason else None,
        "requested_by": cert.requested_by,
        "approved_by": cert.approved_by,
    }


mcp = FastMCP("Certifactory", instructions="PKI certificate management. Authenticate with a cf_ API token.")


@mcp.tool()
def list_cas(token: str, status: str | None = None) -> str:
    """List all certificate authorities. Optionally filter by status (active, disabled)."""
    db = SessionLocal()
    try:
        user = resolve_user(token, db)
        _check_role(user, UserRole.admin, UserRole.operator, UserRole.auditor)
        query = db.query(CertificateAuthority)
        if status:
            query = query.filter(CertificateAuthority.status == CAStatus(status))
        cas = query.all()
        return str([_ca_to_dict(ca) for ca in cas])
    finally:
        db.close()


@mcp.tool()
def get_ca(token: str, ca_id: str | None = None, name: str | None = None) -> str:
    """Get detailed information about a CA by ID or name. Provide one of ca_id or name."""
    db = SessionLocal()
    try:
        user = resolve_user(token, db)
        _check_role(user, UserRole.admin, UserRole.operator, UserRole.auditor)
        if ca_id:
            ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == ca_id).first()
        elif name:
            ca = db.query(CertificateAuthority).filter(CertificateAuthority.name == name).first()
        else:
            raise ValueError("Provide either ca_id or name")
        if not ca:
            raise ValueError("CA not found")
        return str(_ca_to_dict(ca))
    finally:
        db.close()


@mcp.tool()
def get_ca_chain(token: str, ca_id: str) -> str:
    """Get the full PEM certificate chain for a CA, from the CA up to the root."""
    db = SessionLocal()
    try:
        user = resolve_user(token, db)
        _check_role(user, UserRole.admin, UserRole.operator, UserRole.auditor)
        chain = ca_service.get_chain(db, ca_id)
        if not chain:
            raise ValueError("CA not found")
        return "\n".join(chain)
    finally:
        db.close()


@mcp.tool()
def list_certificates(
    token: str, ca_id: str | None = None, status: str | None = None,
    search: str | None = None, sort_by: str = "created_at",
    sort_order: str = "desc", page: int = 1, per_page: int = 25,
) -> str:
    """Search and list certificates. Filter by ca_id, status (active/pending/revoked/expired), or search by subject DN."""
    db = SessionLocal()
    try:
        user = resolve_user(token, db)
        _check_role(user, UserRole.admin, UserRole.operator, UserRole.auditor, UserRole.requester)
        query = db.query(Certificate)
        if user.role == UserRole.requester:
            query = query.filter(Certificate.requested_by == user.id)
        if ca_id:
            query = query.filter(Certificate.ca_id == ca_id)
        if status:
            query = query.filter(Certificate.status == CertificateStatus(status))
        if search:
            query = query.filter(Certificate.subject_dn.ilike(f"%{search}%"))
        total = query.count()
        sort_col = getattr(Certificate, sort_by, Certificate.created_at)
        order = sort_col.asc() if sort_order == "asc" else sort_col.desc()
        items = query.order_by(order).offset((page - 1) * per_page).limit(per_page).all()
        return str({"total": total, "page": page, "items": [_cert_to_dict(c) for c in items]})
    finally:
        db.close()


@mcp.tool()
def get_certificate(token: str, cert_id: str) -> str:
    """Get detailed information about a specific certificate by ID."""
    db = SessionLocal()
    try:
        user = resolve_user(token, db)
        _check_role(user, UserRole.admin, UserRole.operator, UserRole.auditor, UserRole.requester)
        cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
        if not cert:
            raise ValueError("Certificate not found")
        if user.role == UserRole.requester and cert.requested_by != user.id:
            raise ValueError("Certificate not found")
        return str(_cert_to_dict(cert))
    finally:
        db.close()


@mcp.tool()
def get_crl_info(token: str, ca_id: str) -> str:
    """Get CRL (Certificate Revocation List) status for a CA."""
    db = SessionLocal()
    try:
        user = resolve_user(token, db)
        _check_role(user, UserRole.admin, UserRole.operator)
        crl = crl_service.get_latest_crl(db, ca_id)
        if not crl:
            return "No CRL generated yet for this CA"
        return str({
            "crl_number": crl.crl_number,
            "this_update": crl.this_update.isoformat(),
            "next_update": crl.next_update.isoformat(),
        })
    finally:
        db.close()
