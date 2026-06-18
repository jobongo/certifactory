import fnmatch
import secrets
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from sqlalchemy.orm import Session

from app.models import AcmeAccount, AcmeAuthorization, AcmeOrder, Certificate, CertificateAuthority, User, UserRole
from app.services.acme_challenges import validate_http_01, validate_dns_01, validate_tls_alpn_01
from app.services.acme_jws import b64url_encode, jwk_thumbprint
from app.services.auth_service import AuthService
from app.services.ca_service import CAService
from app.services.certificate_service import CertificateService

cert_service = CertificateService()
ca_svc = CAService()

auth_service = AuthService()

_SYSTEM_USERNAME = "acme-service"


class AcmeService:
    def get_system_user_id(self, db: Session) -> str:
        user = db.query(User).filter(User.username == _SYSTEM_USERNAME).first()
        if user:
            return user.id
        import secrets as _secrets
        user = User(
            username=_SYSTEM_USERNAME,
            email="acme-service@certifactory.local",
            password_hash=auth_service.hash_password(_secrets.token_urlsafe(32)),
            role=UserRole.requester,
            is_active=True,
            can_self_approve=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id

    def get_account_by_thumbprint(self, db: Session, thumbprint: str) -> AcmeAccount | None:
        return db.query(AcmeAccount).filter(AcmeAccount.jwk_thumbprint == thumbprint).first()

    def get_or_create_account(self, db: Session, jwk: dict, contact: list | None, only_return_existing: bool) -> AcmeAccount:
        thumbprint = jwk_thumbprint(jwk)
        existing = self.get_account_by_thumbprint(db, thumbprint)
        if existing:
            return existing
        if only_return_existing:
            raise ValueError("accountDoesNotExist")
        account = AcmeAccount(jwk=jwk, jwk_thumbprint=thumbprint, contact=contact, status="active")
        db.add(account)
        db.commit()
        db.refresh(account)
        return account

    def domain_allowed(self, allowed_domains: str, domain: str) -> bool:
        patterns = [p.strip() for p in allowed_domains.split(",") if p.strip()]
        if not patterns:
            return True
        return any(fnmatch.fnmatch(domain, pattern) for pattern in patterns)

    def new_token(self) -> str:
        return b64url_encode(secrets.token_bytes(32))

    def _now(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def create_order(self, db: Session, account_id: str, ca_id: str, identifiers: list, not_before, not_after) -> AcmeOrder:
        expires = self._now() + timedelta(days=7)
        order = AcmeOrder(
            account_id=account_id, ca_id=ca_id, status="pending",
            identifiers=identifiers, not_before=not_before, not_after=not_after,
            expires=expires,
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        for ident in identifiers:
            challenges = [
                {"type": ctype, "token": self.new_token(), "status": "pending", "validated": None, "error": None}
                for ctype in ("http-01", "dns-01", "tls-alpn-01")
            ]
            authz = AcmeAuthorization(
                order_id=order.id, identifier_type=ident["type"], identifier_value=ident["value"],
                status="pending", challenges=challenges, expires=expires,
            )
            db.add(authz)
        db.commit()
        return order

    def get_order(self, db: Session, order_id: str) -> AcmeOrder | None:
        return db.query(AcmeOrder).filter(AcmeOrder.id == order_id).first()

    def get_authorization(self, db: Session, authz_id: str) -> AcmeAuthorization | None:
        return db.query(AcmeAuthorization).filter(AcmeAuthorization.id == authz_id).first()

    def list_authorizations(self, db: Session, order_id: str) -> list:
        return db.query(AcmeAuthorization).filter(AcmeAuthorization.order_id == order_id).all()

    def process_challenge(self, db: Session, authz_id: str, challenge_type: str, jwk: dict):
        authz = self.get_authorization(db, authz_id)
        if not authz:
            raise ValueError("malformed")
        validators = {
            "http-01": validate_http_01,
            "dns-01": validate_dns_01,
            "tls-alpn-01": validate_tls_alpn_01,
        }
        validator = validators.get(challenge_type)
        if not validator:
            raise ValueError("malformed")
        token = None
        challenges = list(authz.challenges)
        for ch in challenges:
            if ch["type"] == challenge_type:
                token = ch["token"]
        if token is None:
            raise ValueError("malformed")

        ok = validator(authz.identifier_value, token, jwk)
        for ch in challenges:
            if ch["type"] == challenge_type:
                ch["status"] = "valid" if ok else "invalid"
                ch["validated"] = self._now().isoformat() if ok else None
                ch["error"] = None if ok else "Validation failed"
        authz.challenges = challenges
        authz.status = "valid" if ok else "invalid"
        db.commit()
        db.refresh(authz)

        if ok:
            order = self.get_order(db, authz.order_id)
            authzs = self.list_authorizations(db, order.id)
            if all(a.status == "valid" for a in authzs):
                order.status = "ready"
                db.commit()
        return authz

    def finalize_order(self, db: Session, order_id: str, csr_der: bytes):
        order = self.get_order(db, order_id)
        if not order:
            raise ValueError("malformed")
        if order.status != "ready":
            raise ValueError("orderNotReady")

        try:
            csr = x509.load_der_x509_csr(csr_der)
        except Exception:
            raise ValueError("badCSR")
        csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode()

        csr_domains = set()
        try:
            san = csr.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            for name in san.value:
                if isinstance(name, x509.DNSName):
                    csr_domains.add(name.value)
        except x509.ExtensionNotFound:
            pass
        for attr in csr.subject:
            if attr.oid == x509.oid.NameOID.COMMON_NAME:
                csr_domains.add(attr.value)

        order_domains = {i["value"] for i in order.identifiers}
        if csr_domains != order_domains:
            raise ValueError("badCSR")

        order.status = "processing"
        db.commit()

        system_user_id = self.get_system_user_id(db)
        cert = cert_service.submit_csr(db, system_user_id, {
            "ca_id": order.ca_id, "csr_pem": csr_pem, "type": "server",
        })
        from app.models import CertificateStatus
        if cert.status == CertificateStatus.pending:
            cert = cert_service.approve(db, system_user_id, cert.id, _skip_self_check=True)

        order.certificate_id = cert.id
        order.status = "valid"
        db.commit()
        db.refresh(order)
        return order

    def get_order_certificate_pem(self, db: Session, order_id: str) -> str:
        order = self.get_order(db, order_id)
        if not order or not order.certificate_id:
            raise ValueError("malformed")
        cert = db.query(Certificate).filter(Certificate.id == order.certificate_id).first()
        if not cert or not cert.certificate_pem:
            raise ValueError("malformed")
        chain = ca_svc.get_chain(db, order.ca_id)
        parts = [cert.certificate_pem.strip()] + [c.strip() for c in chain]
        return "\n".join(parts) + "\n"

    def revoke_certificate(self, db: Session, cert_der: bytes) -> None:
        cert = x509.load_der_x509_certificate(cert_der)
        serial_hex = format(cert.serial_number, "x")
        record = db.query(Certificate).filter(Certificate.serial_number == serial_hex).first()
        if not record:
            raise ValueError("malformed")
        from app.models import CertificateStatus
        if record.status != CertificateStatus.active:
            raise ValueError("alreadyRevoked")
        system_user_id = self.get_system_user_id(db)
        cert_service.revoke(db, system_user_id, record.id, "unspecified")


acme_service = AcmeService()
