import fnmatch
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import AcmeAccount, AcmeAuthorization, AcmeOrder, User, UserRole
from app.services.acme_jws import b64url_encode, jwk_thumbprint
from app.services.auth_service import AuthService

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


acme_service = AcmeService()
