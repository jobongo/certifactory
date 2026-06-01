import pytest


@pytest.fixture
def root_ca(client, admin_headers):
    return client.post(
        "/api/v1/cas",
        json={
            "name": "Test CA",
            "subject": {"CN": "Test CA", "O": "Test", "C": "US"},
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 3650,
            "auto_approve": True,
        },
        headers=admin_headers,
    ).json()


@pytest.fixture
def approval_ca(client, admin_headers):
    return client.post(
        "/api/v1/cas",
        json={
            "name": "Approval CA",
            "subject": {"CN": "Approval CA", "O": "Test", "C": "US"},
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 3650,
            "auto_approve": False,
        },
        headers=admin_headers,
    ).json()


def test_issue_certificate_auto_approve(client, admin_headers, root_ca):
    response = client.post(
        "/api/v1/certificates",
        json={
            "ca_id": root_ca["id"],
            "subject": {"CN": "test.example.com"},
            "san": [{"type": "DNS", "value": "test.example.com"}],
            "type": "server",
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 365,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "active"
    assert data["certificate_pem"] is not None


def test_certificate_pending_approval(client, admin_headers, approval_ca):
    response = client.post(
        "/api/v1/certificates",
        json={
            "ca_id": approval_ca["id"],
            "subject": {"CN": "pending.example.com"},
            "san": [{"type": "DNS", "value": "pending.example.com"}],
            "type": "server",
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 365,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending"


def test_approve_certificate(client, admin_headers, operator_headers, approval_ca):
    cert = client.post(
        "/api/v1/certificates",
        json={
            "ca_id": approval_ca["id"],
            "subject": {"CN": "approve.example.com"},
            "san": [{"type": "DNS", "value": "approve.example.com"}],
            "type": "server",
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 365,
        },
        headers=admin_headers,
    ).json()
    response = client.post(f"/api/v1/certificates/{cert['id']}/approve", headers=operator_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "active"
    assert response.json()["certificate_pem"] is not None


def test_revoke_certificate(client, admin_headers, root_ca):
    cert = client.post(
        "/api/v1/certificates",
        json={
            "ca_id": root_ca["id"],
            "subject": {"CN": "revoke.example.com"},
            "san": [{"type": "DNS", "value": "revoke.example.com"}],
            "type": "server",
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 365,
        },
        headers=admin_headers,
    ).json()
    response = client.post(
        f"/api/v1/certificates/{cert['id']}/revoke",
        json={"reason": "key_compromise"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "revoked"


def test_download_pem(client, admin_headers, root_ca):
    cert = client.post(
        "/api/v1/certificates",
        json={
            "ca_id": root_ca["id"],
            "subject": {"CN": "dl.example.com"},
            "san": [{"type": "DNS", "value": "dl.example.com"}],
            "type": "server",
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 365,
        },
        headers=admin_headers,
    ).json()
    response = client.get(f"/api/v1/certificates/{cert['id']}/download?format=pem", headers=admin_headers)
    assert response.status_code == 200


def test_approve_self_request_allowed_when_can_self_approve(client, admin_headers, admin_user, db):
    admin_user.can_self_approve = True
    db.commit()

    ca_data = {
        "name": "Test CA", "key_algorithm": "RSA", "key_size": 2048,
        "validity_days": 365, "auto_approve": False,
        "subject": {"CN": "Test CA"}
    }
    ca = client.post("/api/v1/cas", json=ca_data, headers=admin_headers).json()

    cert_data = {
        "ca_id": ca["id"], "subject": {"CN": "self-approve-test"},
        "type": "server", "key_algorithm": "RSA", "key_size": 2048, "validity_days": 90
    }
    cert = client.post("/api/v1/certificates", json=cert_data, headers=admin_headers).json()
    assert cert["status"] == "pending"

    resp = client.post(f"/api/v1/certificates/{cert['id']}/approve", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


def test_approve_self_request_blocked_when_cannot_self_approve(client, admin_headers, admin_user, db):
    admin_user.can_self_approve = False
    db.commit()

    ca_data = {
        "name": "Test CA 3", "key_algorithm": "RSA", "key_size": 2048,
        "validity_days": 365, "auto_approve": False,
        "subject": {"CN": "Test CA 3"}
    }
    ca = client.post("/api/v1/cas", json=ca_data, headers=admin_headers).json()

    cert_data = {
        "ca_id": ca["id"], "subject": {"CN": "no-self-approve-test"},
        "type": "server", "key_algorithm": "RSA", "key_size": 2048, "validity_days": 90
    }
    cert = client.post("/api/v1/certificates", json=cert_data, headers=admin_headers).json()
    assert cert["status"] == "pending"

    resp = client.post(f"/api/v1/certificates/{cert['id']}/approve", headers=admin_headers)
    assert resp.status_code == 400
    assert "cannot approve" in resp.json()["detail"].lower()


def test_deny_own_request_allowed(client, admin_headers, admin_user):
    ca_data = {
        "name": "Test CA 2", "key_algorithm": "RSA", "key_size": 2048,
        "validity_days": 365, "auto_approve": False,
        "subject": {"CN": "Test CA 2"}
    }
    ca = client.post("/api/v1/cas", json=ca_data, headers=admin_headers).json()

    cert_data = {
        "ca_id": ca["id"], "subject": {"CN": "self-deny-test"},
        "type": "server", "key_algorithm": "RSA", "key_size": 2048, "validity_days": 90
    }
    cert = client.post("/api/v1/certificates", json=cert_data, headers=admin_headers).json()

    resp = client.post(f"/api/v1/certificates/{cert['id']}/deny", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "denied"


def test_submit_csr(client, admin_headers, root_ca):
    from app.services.crypto_service import CryptoService

    crypto = CryptoService()
    key = crypto.generate_key("RSA", 2048)
    csr = crypto.generate_csr(key, {"CN": "csr.example.com"}, [{"type": "DNS", "value": "csr.example.com"}])
    response = client.post(
        "/api/v1/certificates/csr",
        json={"ca_id": root_ca["id"], "csr_pem": csr, "type": "server", "validity_days": 365},
        headers=admin_headers,
    )
    assert response.status_code == 201
    assert response.json()["status"] == "active"
