import pytest
from app.services.acme_service import AcmeService

svc = AcmeService()
JWK = {"kty": "RSA", "n": "abc", "e": "AQAB"}


def test_system_user_created_once(db):
    uid1 = svc.get_system_user_id(db)
    uid2 = svc.get_system_user_id(db)
    assert uid1 == uid2
    from app.models import User
    user = db.query(User).filter(User.id == uid1).first()
    assert user.username == "acme-service"


def test_get_or_create_account_creates(db):
    acct = svc.get_or_create_account(db, JWK, ["mailto:a@b.com"], only_return_existing=False)
    assert acct.id is not None
    assert acct.contact == ["mailto:a@b.com"]


def test_get_or_create_account_returns_existing(db):
    a1 = svc.get_or_create_account(db, JWK, None, only_return_existing=False)
    a2 = svc.get_or_create_account(db, JWK, None, only_return_existing=False)
    assert a1.id == a2.id


def test_only_return_existing_raises_when_missing(db):
    with pytest.raises(ValueError, match="accountDoesNotExist"):
        svc.get_or_create_account(db, {"kty": "RSA", "n": "zzz", "e": "AQAB"}, None, only_return_existing=True)


def test_domain_allowed_empty_allows_all():
    assert svc.domain_allowed("", "anything.com") is True


def test_domain_allowed_exact_match():
    assert svc.domain_allowed("example.com,test.com", "example.com") is True
    assert svc.domain_allowed("example.com", "other.com") is False


def test_domain_allowed_wildcard():
    assert svc.domain_allowed("*.example.com", "www.example.com") is True
    assert svc.domain_allowed("*.example.com", "example.com") is False
