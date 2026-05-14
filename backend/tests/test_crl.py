import pytest


@pytest.fixture
def ca_with_revoked(client, admin_headers):
    ca = client.post(
        "/api/v1/cas",
        json={
            "name": "CRL CA",
            "subject": {"CN": "CRL CA", "O": "Test", "C": "US"},
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 3650,
            "auto_approve": True,
        },
        headers=admin_headers,
    ).json()

    cert = client.post(
        "/api/v1/certificates",
        json={
            "ca_id": ca["id"],
            "subject": {"CN": "revoked.example.com"},
            "san": [{"type": "DNS", "value": "revoked.example.com"}],
            "type": "server",
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 365,
        },
        headers=admin_headers,
    ).json()

    client.post(f"/api/v1/certificates/{cert['id']}/revoke", json={"reason": "key_compromise"}, headers=admin_headers)
    return ca


def test_generate_crl(client, admin_headers, ca_with_revoked):
    response = client.post(f"/api/v1/cas/{ca_with_revoked['id']}/crl/generate", headers=admin_headers)
    assert response.status_code == 200
    assert "-----BEGIN X509 CRL-----" in response.json()["crl_pem"]


def test_download_crl(client, admin_headers, ca_with_revoked):
    client.post(f"/api/v1/cas/{ca_with_revoked['id']}/crl/generate", headers=admin_headers)
    response = client.get(f"/api/v1/cas/{ca_with_revoked['id']}/crl", headers=admin_headers)
    assert response.status_code == 200
