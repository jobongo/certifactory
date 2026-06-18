import json
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes

from app.services.acme_jws import b64url_encode


def _rsa_jwk(public_key):
    nums = public_key.public_numbers()
    def to_b64(n):
        return b64url_encode(n.to_bytes((n.bit_length() + 7) // 8, "big"))
    return {"kty": "RSA", "n": to_b64(nums.n), "e": to_b64(nums.e)}


def _signed_jws(key, jwk, url, nonce, payload_obj, kid=None):
    protected = {"alg": "RS256", "nonce": nonce, "url": url}
    if kid:
        protected["kid"] = kid
    else:
        protected["jwk"] = jwk
    protected_b64 = b64url_encode(json.dumps(protected).encode())
    payload_b64 = b64url_encode(json.dumps(payload_obj).encode()) if payload_obj is not None else ""
    signing_input = f"{protected_b64}.{payload_b64}".encode()
    sig = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return {"protected": protected_b64, "payload": payload_b64, "signature": b64url_encode(sig)}


def _enable(db):
    from app.models.setting import Setting
    db.add(Setting(key="acme_enabled", value="true"))
    db.add(Setting(key="acme_default_ca_id", value="ca-1"))
    db.commit()


def test_new_account_with_valid_jws(client, db):
    _enable(db)
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = _rsa_jwk(key.public_key())
    url = "http://testserver/acme/new-account"
    body = _signed_jws(key, jwk, url, nonce, {"contact": ["mailto:a@b.com"], "termsOfServiceAgreed": True})
    resp = client.post("/acme/new-account", json=body, headers={"Content-Type": "application/jose+json"})
    assert resp.status_code in (200, 201)
    assert "Replay-Nonce" in resp.headers


def test_bad_nonce_rejected(client, db):
    _enable(db)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = _rsa_jwk(key.public_key())
    url = "http://testserver/acme/new-account"
    body = _signed_jws(key, jwk, url, "fake-nonce", {"termsOfServiceAgreed": True})
    resp = client.post("/acme/new-account", json=body, headers={"Content-Type": "application/jose+json"})
    assert resp.status_code == 400
    assert "badNonce" in resp.json()["type"]


def test_url_mismatch_rejected(client, db):
    _enable(db)
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = _rsa_jwk(key.public_key())
    # Sign with the WRONG url — not the endpoint being POSTed to
    wrong_url = "http://testserver/acme/WRONG"
    body = _signed_jws(key, jwk, wrong_url, nonce, {"termsOfServiceAgreed": True})
    resp = client.post("/acme/new-account", json=body, headers={"Content-Type": "application/jose+json"})
    assert resp.status_code == 401
    assert resp.json()["type"].endswith("unauthorized")


def test_invalid_signature_rejected(client, db):
    _enable(db)
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = _rsa_jwk(key.public_key())
    url = "http://testserver/acme/new-account"
    body = _signed_jws(key, jwk, url, nonce, {"termsOfServiceAgreed": True})
    # Corrupt the signature with a valid-base64url but wrong value
    body["signature"] = b64url_encode(b"\x00" * 256)
    resp = client.post("/acme/new-account", json=body, headers={"Content-Type": "application/jose+json"})
    assert resp.status_code == 401
    assert resp.json()["type"].endswith("unauthorized")


def test_same_jwk_returns_same_account(client, db):
    # Verifies account deduplication: two new-account calls with the same JWK
    # must return the same Location header (kid stability).
    _enable(db)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = _rsa_jwk(key.public_key())
    url = "http://testserver/acme/new-account"

    nonce1 = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    body1 = _signed_jws(key, jwk, url, nonce1, {"termsOfServiceAgreed": True})
    resp1 = client.post("/acme/new-account", json=body1, headers={"Content-Type": "application/jose+json"})
    assert resp1.status_code in (200, 201)
    location1 = resp1.headers.get("Location", "")
    assert location1 != ""

    nonce2 = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    body2 = _signed_jws(key, jwk, url, nonce2, {"termsOfServiceAgreed": True})
    resp2 = client.post("/acme/new-account", json=body2, headers={"Content-Type": "application/jose+json"})
    assert resp2.status_code in (200, 201)
    location2 = resp2.headers.get("Location", "")
    assert location2 == location1


def test_registration_closed_rejects_new_jwk(client, db):
    _enable(db)
    # Close registration
    from app.models.setting import Setting
    db.add(Setting(key="acme_registration_open", value="false"))
    db.commit()

    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = _rsa_jwk(key.public_key())
    url = "http://testserver/acme/new-account"
    body = _signed_jws(key, jwk, url, nonce, {"termsOfServiceAgreed": True})
    resp = client.post("/acme/new-account", json=body, headers={"Content-Type": "application/jose+json"})
    assert resp.status_code == 403
