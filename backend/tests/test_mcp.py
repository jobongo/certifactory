import pytest
from app.mcp_server import resolve_user
from app.models import User, UserRole
from app.models.api_token import ApiToken
from app.services.auth_service import AuthService


@pytest.fixture
def mcp_user(db):
    auth = AuthService()
    user = User(
        username="mcp_agent", email="agent@test.com",
        password_hash=auth.hash_password("agent123"), role=UserRole.operator,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def mcp_token(db, mcp_user):
    raw = ApiToken.generate_token()
    token = ApiToken(user_id=mcp_user.id, name="mcp-test", token_hash=ApiToken.hash_token(raw), token_prefix=raw[:10])
    db.add(token)
    db.commit()
    return raw


def test_resolve_user_valid_token(db, mcp_user, mcp_token):
    user = resolve_user(mcp_token, db)
    assert user.id == mcp_user.id
    assert user.role == UserRole.operator


def test_resolve_user_invalid_token(db):
    with pytest.raises(ValueError, match="Invalid or revoked API token"):
        resolve_user("cf_invalidtoken", db)


def test_resolve_user_missing_prefix(db):
    with pytest.raises(ValueError, match="API token required"):
        resolve_user("not_a_cf_token", db)


def test_resolve_user_none(db):
    with pytest.raises(ValueError, match="API token required"):
        resolve_user(None, db)
