from datetime import datetime, timezone
import pytest
from app.models import AcmeAccount, AcmeOrder, AcmeAuthorization, CertificateAuthority, CAType, User, UserRole
from app.services.auth_service import AuthService


@pytest.fixture
def test_ca(db):
    """Create a test CA for ACME orders"""
    # Create a user first (required for created_by)
    auth = AuthService()
    user = User(username="test_ca_user", email="ca@test.com", password_hash=auth.hash_password("test123"), role=UserRole.admin)
    db.add(user)
    db.commit()

    # Create the CA
    ca = CertificateAuthority(
        id="ca-1",
        name="Test CA",
        type=CAType.root,
        private_key_encrypted="test-key",
        certificate_pem="test-cert",
        key_algorithm="RSA",
        key_size=2048,
        subject_dn="CN=Test CA",
        serial_number="123456",
        not_before=datetime.now(timezone.utc).replace(tzinfo=None),
        not_after=datetime.now(timezone.utc).replace(tzinfo=None),
        created_by=user.id
    )
    db.add(ca)
    db.commit()
    return ca


def test_acme_account_persists(db):
    acct = AcmeAccount(jwk={"kty": "RSA", "n": "abc", "e": "AQAB"}, jwk_thumbprint="thumb123", contact=["mailto:a@b.com"], status="active")
    db.add(acct)
    db.commit()
    db.refresh(acct)
    assert acct.id is not None
    assert acct.jwk["kty"] == "RSA"
    assert acct.status == "active"


def test_acme_order_persists(db, test_ca):
    acct = AcmeAccount(jwk={"kty": "RSA"}, jwk_thumbprint="t1", contact=[], status="active")
    db.add(acct)
    db.commit()
    order = AcmeOrder(account_id=acct.id, ca_id="ca-1", status="pending", identifiers=[{"type": "dns", "value": "example.com"}], expires=datetime.now(timezone.utc).replace(tzinfo=None))
    db.add(order)
    db.commit()
    db.refresh(order)
    assert order.id is not None
    assert order.identifiers[0]["value"] == "example.com"
    assert order.certificate_id is None


def test_acme_authorization_persists(db, test_ca):
    acct = AcmeAccount(jwk={"kty": "RSA"}, jwk_thumbprint="t2", contact=[], status="active")
    db.add(acct)
    db.commit()
    order = AcmeOrder(account_id=acct.id, ca_id="ca-1", status="pending", identifiers=[], expires=datetime.now(timezone.utc).replace(tzinfo=None))
    db.add(order)
    db.commit()
    authz = AcmeAuthorization(order_id=order.id, identifier_type="dns", identifier_value="example.com", status="pending", challenges=[{"type": "http-01", "token": "tok", "status": "pending"}], expires=datetime.now(timezone.utc).replace(tzinfo=None))
    db.add(authz)
    db.commit()
    db.refresh(authz)
    assert authz.id is not None
    assert authz.challenges[0]["type"] == "http-01"
