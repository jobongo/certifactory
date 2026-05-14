import pytest
from cryptography.x509 import ocsp, load_pem_x509_certificate
from cryptography.hazmat.primitives import hashes, serialization


@pytest.fixture
def ca_and_cert(client, admin_headers):
    ca = client.post(
        "/api/v1/cas",
        json={
            "name": "OCSP CA",
            "subject": {"CN": "OCSP CA", "O": "Test", "C": "US"},
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
            "subject": {"CN": "ocsp.example.com"},
            "san": [{"type": "DNS", "value": "ocsp.example.com"}],
            "type": "server",
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 365,
        },
        headers=admin_headers,
    ).json()
    return ca, cert


def test_ocsp_good_status(client, ca_and_cert):
    ca, cert = ca_and_cert
    ca_cert = load_pem_x509_certificate(ca["certificate_pem"].encode())
    ee_cert = load_pem_x509_certificate(cert["certificate_pem"].encode())

    ocsp_req = ocsp.OCSPRequestBuilder().add_certificate(ee_cert, ca_cert, hashes.SHA256()).build()
    req_bytes = ocsp_req.public_bytes(serialization.Encoding.DER)

    response = client.post(
        f"/api/v1/ocsp/{ca['id']}",
        content=req_bytes,
        headers={"Content-Type": "application/ocsp-request"},
    )
    assert response.status_code == 200
    ocsp_resp = ocsp.load_der_ocsp_response(response.content)
    assert ocsp_resp.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL
    assert ocsp_resp.certificate_status == ocsp.OCSPCertStatus.GOOD
