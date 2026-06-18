import fnmatch

from sqlalchemy.orm import Session

from app.models import AcmeAccount, User, UserRole
from app.services.acme_jws import jwk_thumbprint
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


acme_service = AcmeService()
