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
    admin = User(username="acrev", email="acrev@t.com", password_hash=AuthService().hash_password("x"), role=UserRole.admin)
    db.add(admin); db.commit(); db.refresh(admin)
    return ca_service.create_root_ca(db, admin.id, {
        "name": "RevCA", "description": None, "subject": {"CN": "RevCA"},
        "key_algorithm": "RSA", "key_size": 2048, "validity_days": 3650,
        "max_path_length": None, "auto_approve": True, "crl_distribution_url": None, "ocsp_url": None,
    })


def _register_account(client, key):
    jwk = _rsa_jwk(key.public_key())
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    r = client.post("/acme/new-account", json=_jws(key, "http://testserver/acme/new-account", nonce, {"termsOfServiceAgreed": True}, jwk=jwk), headers={"Content-Type": "application/jose+json"})
    return r.headers["Location"]


def test_revoke_certificate(client, db):
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
    order = client.post("/acme/new-order", json=_jws(key, "http://testserver/acme/new-order", nonce, {"identifiers": [{"type": "dns", "value": "revoke-me.com"}]}, kid=account_url), headers={"Content-Type": "application/jose+json"}).json()
    order_id = order["finalize"].split("/order/")[1].split("/finalize")[0]
    authz_id = order["authorizations"][0].split("/authz/")[1]
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    with patch("app.services.acme_service.validate_http_01", return_value=True):
        client.post(f"/acme/challenge/{authz_id}/http-01", json=_jws(key, f"http://testserver/acme/challenge/{authz_id}/http-01", nonce, {}, kid=account_url), headers={"Content-Type": "application/jose+json"})
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    client.post(f"/acme/order/{order_id}/finalize", json=_jws(key, f"http://testserver/acme/order/{order_id}/finalize", nonce, {"csr": b64url_encode(_csr_der("revoke-me.com"))}, kid=account_url), headers={"Content-Type": "application/jose+json"})
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    cert_pem = client.post(f"/acme/order/{order_id}/cert", json=_jws(key, f"http://testserver/acme/order/{order_id}/cert", nonce, None, kid=account_url), headers={"Content-Type": "application/jose+json"}).text

    leaf = cert_pem.split("-----END CERTIFICATE-----")[0] + "-----END CERTIFICATE-----\n"
    der = x509.load_pem_x509_certificate(leaf.encode()).public_bytes(serialization.Encoding.DER)
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    resp = client.post("/acme/revoke-cert", json=_jws(key, "http://testserver/acme/revoke-cert", nonce, {"certificate": b64url_encode(der)}, kid=account_url), headers={"Content-Type": "application/jose+json"})
    assert resp.status_code == 200


def test_revoke_cross_account_forbidden(client, db):
    """A second account cannot revoke another account's certificate."""
    ca = _make_ca(db)
    from app.models.setting import Setting
    db.add(Setting(key="acme_enabled", value="true"))
    db.add(Setting(key="acme_default_ca_id", value=ca.id))
    db.commit()

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    account_url = _register_account(client, key)

    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    order = client.post("/acme/new-order", json=_jws(key, "http://testserver/acme/new-order", nonce, {"identifiers": [{"type": "dns", "value": "rev-own.com"}]}, kid=account_url), headers={"Content-Type": "application/jose+json"}).json()
    order_id = order["finalize"].split("/order/")[1].split("/finalize")[0]
    authz_id = order["authorizations"][0].split("/authz/")[1]

    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    with patch("app.services.acme_service.validate_http_01", return_value=True):
        client.post(f"/acme/challenge/{authz_id}/http-01", json=_jws(key, f"http://testserver/acme/challenge/{authz_id}/http-01", nonce, {}, kid=account_url), headers={"Content-Type": "application/jose+json"})

    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    client.post(f"/acme/order/{order_id}/finalize", json=_jws(key, f"http://testserver/acme/order/{order_id}/finalize", nonce, {"csr": b64url_encode(_csr_der("rev-own.com"))}, kid=account_url), headers={"Content-Type": "application/jose+json"})

    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    cert_pem = client.post(f"/acme/order/{order_id}/cert", json=_jws(key, f"http://testserver/acme/order/{order_id}/cert", nonce, None, kid=account_url), headers={"Content-Type": "application/jose+json"}).text
    leaf = cert_pem.split("-----END CERTIFICATE-----")[0] + "-----END CERTIFICATE-----\n"
    der = x509.load_pem_x509_certificate(leaf.encode()).public_bytes(serialization.Encoding.DER)

    key2 = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    account_url2 = _register_account(client, key2)

    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    resp = client.post("/acme/revoke-cert", json=_jws(key2, "http://testserver/acme/revoke-cert", nonce, {"certificate": b64url_encode(der)}, kid=account_url2), headers={"Content-Type": "application/jose+json"})
    assert resp.status_code == 400
    assert "unauthorized" in resp.json()["type"]
