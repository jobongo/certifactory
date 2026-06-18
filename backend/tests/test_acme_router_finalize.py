import json
from unittest.mock import patch
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509.oid import NameOID
from app.services.acme_jws import b64url_encode


def _rsa_jwk(pub):
    n = pub.public_numbers()
    f = lambda v: b64url_encode(v.to_bytes((v.bit_length() + 7) // 8, "big"))
    return {"kty": "RSA", "n": f(n.n), "e": f(n.e)}


def _jws(key, url, nonce, payload, jwk=None, kid=None):
    protected = {"alg": "RS256", "nonce": nonce, "url": url}
    if kid:
        protected["kid"] = kid
    else:
        protected["jwk"] = jwk
    pb = b64url_encode(json.dumps(protected).encode())
    yb = b64url_encode(json.dumps(payload).encode()) if payload is not None else ""
    sig = key.sign(f"{pb}.{yb}".encode(), padding.PKCS1v15(), hashes.SHA256())
    return {"protected": pb, "payload": yb, "signature": b64url_encode(sig)}


def _csr_der(domain):
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    csr = (x509.CertificateSigningRequestBuilder()
           .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, domain)]))
           .add_extension(x509.SubjectAlternativeName([x509.DNSName(domain)]), critical=False)
           .sign(k, hashes.SHA256()))
    return csr.public_bytes(serialization.Encoding.DER)


def _make_ca(db):
    from app.routers.cas import ca_service
    from app.models import User, UserRole
    from app.services.auth_service import AuthService
    admin = User(username="acfin", email="acfin@t.com", password_hash=AuthService().hash_password("x"), role=UserRole.admin)
    db.add(admin); db.commit(); db.refresh(admin)
    return ca_service.create_root_ca(db, admin.id, {
        "name": "FinCA", "description": None, "subject": {"CN": "FinCA"},
        "key_algorithm": "RSA", "key_size": 2048, "validity_days": 3650,
        "max_path_length": None, "auto_approve": True, "crl_distribution_url": None, "ocsp_url": None,
    })


def test_full_order_to_certificate(client, db):
    ca = _make_ca(db)
    from app.models.setting import Setting
    db.add(Setting(key="acme_enabled", value="true"))
    db.add(Setting(key="acme_default_ca_id", value=ca.id))
    db.commit()

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = _rsa_jwk(key.public_key())
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    r = client.post("/acme/new-account", json=_jws(key, "http://testserver/acme/new-account", nonce, {"termsOfServiceAgreed": True}, jwk=jwk), headers={"Content-Type": "application/jose+json"})
    account_url = r.headers["Location"]

    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    order = client.post("/acme/new-order", json=_jws(key, "http://testserver/acme/new-order", nonce, {"identifiers": [{"type": "dns", "value": "acme-e2e.com"}]}, kid=account_url), headers={"Content-Type": "application/jose+json"}).json()
    order_id = order["finalize"].split("/order/")[1].split("/finalize")[0]
    authz_url = order["authorizations"][0]
    authz_id = authz_url.split("/authz/")[1]

    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    with patch("app.services.acme_service.validate_http_01", return_value=True):
        client.post(f"/acme/challenge/{authz_id}/http-01", json=_jws(key, f"http://testserver/acme/challenge/{authz_id}/http-01", nonce, {}, kid=account_url), headers={"Content-Type": "application/jose+json"})

    csr_b64 = b64url_encode(_csr_der("acme-e2e.com"))
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    fin = client.post(f"/acme/order/{order_id}/finalize", json=_jws(key, f"http://testserver/acme/order/{order_id}/finalize", nonce, {"csr": csr_b64}, kid=account_url), headers={"Content-Type": "application/jose+json"})
    assert fin.status_code == 200
    assert fin.json()["status"] == "valid"
    assert "Replay-Nonce" in fin.headers

    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    cert = client.post(f"/acme/order/{order_id}/cert", json=_jws(key, f"http://testserver/acme/order/{order_id}/cert", nonce, None, kid=account_url), headers={"Content-Type": "application/jose+json"})
    assert cert.status_code == 200
    assert "BEGIN CERTIFICATE" in cert.text
    assert "application/pem-certificate-chain" in cert.headers["content-type"]
    assert "Replay-Nonce" in cert.headers
