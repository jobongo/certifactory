import pytest
from datetime import datetime, timezone
from app.services.acme_service import AcmeService
from app.models import AcmeAuthorization, CertificateAuthority, CAType, User, UserRole
from app.services.auth_service import AuthService

svc = AcmeService()
JWK = {"kty": "RSA", "n": "ord", "e": "AQAB"}


@pytest.fixture(autouse=True)
def test_ca(db):
    auth = AuthService()
    user = User(username="test_ca_user", email="ca@test.com", password_hash=auth.hash_password("test123"), role=UserRole.admin)
    db.add(user)
    db.commit()
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
        created_by=user.id,
    )
    db.add(ca)
    db.commit()
    return ca


def _account(db):
    return svc.get_or_create_account(db, JWK, None, only_return_existing=False)


def test_create_order_creates_authorizations(db):
    acct = _account(db)
    order = svc.create_order(db, acct.id, "ca-1", [{"type": "dns", "value": "a.com"}, {"type": "dns", "value": "b.com"}], None, None)
    assert order.status == "pending"
    authzs = svc.list_authorizations(db, order.id)
    assert len(authzs) == 2
    values = {a.identifier_value for a in authzs}
    assert values == {"a.com", "b.com"}


def test_each_authorization_has_three_challenges(db):
    acct = _account(db)
    order = svc.create_order(db, acct.id, "ca-1", [{"type": "dns", "value": "c.com"}], None, None)
    authz = svc.list_authorizations(db, order.id)[0]
    types = {c["type"] for c in authz.challenges}
    assert types == {"http-01", "dns-01", "tls-alpn-01"}
    for c in authz.challenges:
        assert c["status"] == "pending"
        assert len(c["token"]) > 10


def test_get_order_and_authorization(db):
    acct = _account(db)
    order = svc.create_order(db, acct.id, "ca-1", [{"type": "dns", "value": "d.com"}], None, None)
    assert svc.get_order(db, order.id).id == order.id
    authz = svc.list_authorizations(db, order.id)[0]
    assert svc.get_authorization(db, authz.id).identifier_value == "d.com"
