import pytest
from datetime import datetime, timezone
from unittest.mock import patch
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from app.services.acme_service import AcmeService
from app.services.crypto_service import CryptoService
from app.models import CertificateAuthority, CAType, CAStatus, User, UserRole
from app.services.auth_service import AuthService

svc = AcmeService()
crypto = CryptoService()
JWK = {"kty": "RSA", "n": "fin", "e": "AQAB"}


@pytest.fixture(autouse=True)
def stub_ca(db):
    """Create a stub CA with id='ca-x' to satisfy FK constraints for process_challenge tests."""
    auth = AuthService()
    user = User(
        username="stub_ca_user", email="stubca@test.com",
        password_hash=auth.hash_password("test123"), role=UserRole.admin,
    )
    db.add(user)
    db.commit()
    ca = CertificateAuthority(
        id="ca-x",
        name="Stub CA",
        type=CAType.root,
        private_key_encrypted="stub-key",
        certificate_pem="stub-cert",
        key_algorithm="RSA",
        key_size=2048,
        subject_dn="CN=Stub CA",
        serial_number="000001",
        not_before=datetime.now(timezone.utc).replace(tzinfo=None),
        not_after=datetime.now(timezone.utc).replace(tzinfo=None),
        created_by=user.id,
    )
    db.add(ca)
    db.commit()
    return ca


def _csr_der(domain):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, domain)]))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(domain)]), critical=False)
        .sign(key, hashes.SHA256())
    )
    return csr.public_bytes(serialization.Encoding.DER)


def _ca(db):
    from app.routers.cas import ca_service as real_ca_service
    data = {
        "name": "ACME CA", "description": None, "subject": {"CN": "ACME CA"},
        "key_algorithm": "RSA", "key_size": 2048, "validity_days": 3650,
        "max_path_length": None, "auto_approve": True,
        "crl_distribution_url": None, "ocsp_url": None,
    }
    admin = User(username="acmeadmin", email="acmeadmin@t.com", password_hash=AuthService().hash_password("x"), role=UserRole.admin)
    db.add(admin); db.commit(); db.refresh(admin)
    return real_ca_service.create_root_ca(db, admin.id, data)


def test_process_challenge_success_marks_ready(db):
    acct = svc.get_or_create_account(db, JWK, None, False)
    order = svc.create_order(db, acct.id, "ca-x", [{"type": "dns", "value": "valid.com"}], None, None)
    authz = svc.list_authorizations(db, order.id)[0]
    with patch("app.services.acme_service.validate_http_01", return_value=True):
        updated = svc.process_challenge(db, authz.id, "http-01", JWK)
    assert updated.status == "valid"
    assert svc.get_order(db, order.id).status == "ready"


def test_process_challenge_failure_marks_invalid(db):
    acct = svc.get_or_create_account(db, JWK, None, False)
    order = svc.create_order(db, acct.id, "ca-x", [{"type": "dns", "value": "bad.com"}], None, None)
    authz = svc.list_authorizations(db, order.id)[0]
    with patch("app.services.acme_service.validate_http_01", return_value=False):
        updated = svc.process_challenge(db, authz.id, "http-01", JWK)
    assert updated.status == "invalid"


def test_finalize_issues_certificate(db):
    ca = _ca(db)
    acct = svc.get_or_create_account(db, JWK, None, False)
    order = svc.create_order(db, acct.id, ca.id, [{"type": "dns", "value": "finalize.com"}], None, None)
    authz = svc.list_authorizations(db, order.id)[0]
    with patch("app.services.acme_service.validate_http_01", return_value=True):
        svc.process_challenge(db, authz.id, "http-01", JWK)
    order = svc.finalize_order(db, order.id, _csr_der("finalize.com"))
    assert order.status == "valid"
    assert order.certificate_id is not None
    pem = svc.get_order_certificate_pem(db, order.id)
    assert "BEGIN CERTIFICATE" in pem


def test_finalize_rejects_domain_mismatch(db):
    ca = _ca(db)
    acct = svc.get_or_create_account(db, JWK, None, False)
    order = svc.create_order(db, acct.id, ca.id, [{"type": "dns", "value": "ordered.com"}], None, None)
    authz = svc.list_authorizations(db, order.id)[0]
    with patch("app.services.acme_service.validate_http_01", return_value=True):
        svc.process_challenge(db, authz.id, "http-01", JWK)
    with pytest.raises(ValueError, match="badCSR"):
        svc.finalize_order(db, order.id, _csr_der("different.com"))


def test_multi_domain_order_ready_only_when_all_authzs_valid(db):
    acct = svc.get_or_create_account(db, JWK, None, False)
    order = svc.create_order(
        db, acct.id, "ca-x",
        [{"type": "dns", "value": "multi-a.com"}, {"type": "dns", "value": "multi-b.com"}],
        None, None,
    )
    authzs = svc.list_authorizations(db, order.id)
    assert len(authzs) == 2
    authz_a = next(a for a in authzs if a.identifier_value == "multi-a.com")
    authz_b = next(a for a in authzs if a.identifier_value == "multi-b.com")

    with patch("app.services.acme_service.validate_http_01", return_value=True):
        updated_a = svc.process_challenge(db, authz_a.id, "http-01", JWK)

    assert updated_a.status == "valid"
    assert svc.get_order(db, order.id).status == "pending"

    with patch("app.services.acme_service.validate_http_01", return_value=True):
        updated_b = svc.process_challenge(db, authz_b.id, "http-01", JWK)

    assert updated_b.status == "valid"
    assert svc.get_order(db, order.id).status == "ready"


def test_finalize_rejects_pending_order(db):
    ca = _ca(db)
    acct = svc.get_or_create_account(db, JWK, None, False)
    order = svc.create_order(db, acct.id, ca.id, [{"type": "dns", "value": "pending.com"}], None, None)
    with pytest.raises(ValueError, match="orderNotReady"):
        svc.finalize_order(db, order.id, _csr_der("pending.com"))
