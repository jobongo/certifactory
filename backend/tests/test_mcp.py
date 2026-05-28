import pytest
import app.mcp_server as mcp_server_module
from app.mcp_server import approve_certificate, check_certificate_status, create_certificate, deny_certificate, resolve_user
from app.models import User, UserRole
from app.models.api_token import ApiToken
from app.services.auth_service import AuthService
from tests.conftest import TestingSessionLocal


@pytest.fixture(autouse=True)
def patch_mcp_session():
    """Redirect MCP server SessionLocal to the test database."""
    original = mcp_server_module.SessionLocal
    mcp_server_module.SessionLocal = TestingSessionLocal
    yield
    mcp_server_module.SessionLocal = original


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


@pytest.fixture
def test_ca(client, admin_headers):
    ca_data = {
        "name": "MCP Test CA", "key_algorithm": "RSA", "key_size": 2048,
        "validity_days": 365, "auto_approve": True,
        "subject": {"CN": "MCP Test CA"}
    }
    return client.post("/api/v1/cas", json=ca_data, headers=admin_headers).json()


@pytest.fixture
def manual_ca(client, admin_headers):
    ca_data = {
        "name": "Manual CA", "key_algorithm": "RSA", "key_size": 2048,
        "validity_days": 365, "auto_approve": False,
        "subject": {"CN": "Manual CA"}
    }
    return client.post("/api/v1/cas", json=ca_data, headers=admin_headers).json()


def test_create_certificate_auto_approve(db, mcp_user, mcp_token, test_ca):
    result = create_certificate(
        token=mcp_token, ca_id=test_ca["id"], common_name="agent.example.com",
        type="server", key_algorithm="RSA", key_size=2048, validity_days=90,
    )
    assert "active" in result
    assert "agent.example.com" in result


def test_create_certificate_pending(db, mcp_user, mcp_token, manual_ca):
    result = create_certificate(
        token=mcp_token, ca_id=manual_ca["id"], common_name="pending.example.com",
    )
    assert "pending" in result


def test_approve_self_blocked_via_mcp(db, mcp_user, mcp_token, manual_ca):
    result = create_certificate(
        token=mcp_token, ca_id=manual_ca["id"], common_name="self-block.example.com",
    )
    import ast
    cert_dict = ast.literal_eval(result)
    with pytest.raises(ValueError, match="Cannot approve"):
        approve_certificate(token=mcp_token, cert_id=cert_dict["id"])


def test_deny_self_blocked_via_mcp(db, mcp_user, mcp_token, manual_ca):
    result = create_certificate(
        token=mcp_token, ca_id=manual_ca["id"], common_name="self-deny-mcp.example.com",
    )
    import ast
    cert_dict = ast.literal_eval(result)
    with pytest.raises(ValueError, match="Cannot deny"):
        deny_certificate(token=mcp_token, cert_id=cert_dict["id"])


def test_check_certificate_status_active(db, mcp_user, mcp_token, test_ca):
    result = create_certificate(
        token=mcp_token, ca_id=test_ca["id"], common_name="status-check.example.com",
        type="server", key_algorithm="RSA", key_size=2048, validity_days=90,
    )
    import ast
    cert_dict = ast.literal_eval(result)
    status_result = check_certificate_status(token=mcp_token, cert_id=cert_dict["id"])
    assert "'status': 'active'" in status_result
    assert "status-check.example.com" in status_result
