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


def test_approve_certificate(client, admin_headers, approval_ca):
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
    response = client.post(f"/api/v1/certificates/{cert['id']}/approve", headers=admin_headers)
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
