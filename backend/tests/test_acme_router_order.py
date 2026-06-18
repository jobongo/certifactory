import json
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
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


def _setup(client, db):
    from app.models.setting import Setting
    from app.models import CertificateAuthority, CAType, User, UserRole
    from app.services.auth_service import AuthService
    from datetime import datetime, timezone
    db.add(Setting(key="acme_enabled", value="true"))
    db.add(Setting(key="acme_default_ca_id", value="ca-1"))
    auth = AuthService()
    user = User(username="acme_test_user", email="acme@test.com",
                password_hash=auth.hash_password("test123"), role=UserRole.admin)
    db.add(user)
    db.flush()
    ca = CertificateAuthority(
        id="ca-1", name="Test CA", type=CAType.root,
        private_key_encrypted="test-key", certificate_pem="test-cert",
        key_algorithm="RSA", key_size=2048, subject_dn="CN=Test CA",
        serial_number="123456",
        not_before=datetime.now(timezone.utc).replace(tzinfo=None),
        not_after=datetime.now(timezone.utc).replace(tzinfo=None),
        created_by=user.id,
    )
    db.add(ca)
    db.commit()
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = _rsa_jwk(key.public_key())
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    body = _jws(key, "http://testserver/acme/new-account", nonce, {"termsOfServiceAgreed": True}, jwk=jwk)
    r = client.post("/acme/new-account", json=body, headers={"Content-Type": "application/jose+json"})
    account_url = r.headers["Location"]
    return key, jwk, account_url


def test_new_order_creates_pending_order(client, db):
    key, jwk, account_url = _setup(client, db)
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    body = _jws(key, "http://testserver/acme/new-order", nonce, {"identifiers": [{"type": "dns", "value": "example.com"}]}, kid=account_url)
    resp = client.post("/acme/new-order", json=body, headers={"Content-Type": "application/jose+json"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert len(data["authorizations"]) == 1
    assert "finalize" in data


def test_authz_lists_challenges(client, db):
    key, jwk, account_url = _setup(client, db)
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    body = _jws(key, "http://testserver/acme/new-order", nonce, {"identifiers": [{"type": "dns", "value": "authz.com"}]}, kid=account_url)
    order = client.post("/acme/new-order", json=body, headers={"Content-Type": "application/jose+json"}).json()
    authz_url = order["authorizations"][0]
    authz_path = "/acme" + authz_url.split("/acme", 1)[1]
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    body = _jws(key, authz_url, nonce, None, kid=account_url)
    resp = client.post(authz_path, json=body, headers={"Content-Type": "application/jose+json"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["identifier"]["value"] == "authz.com"
    assert len(data["challenges"]) == 3


def _register_second_account(client):
    key2 = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk2 = _rsa_jwk(key2.public_key())
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    r = client.post("/acme/new-account", json=_jws(key2, "http://testserver/acme/new-account", nonce, {"termsOfServiceAgreed": True}, jwk=jwk2), headers={"Content-Type": "application/jose+json"})
    account_url2 = r.headers["Location"]
    return key2, jwk2, account_url2


def test_get_order_cross_account_forbidden(client, db):
    """A second account cannot read another account's order."""
    key, jwk, account_url = _setup(client, db)
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    order = client.post("/acme/new-order", json=_jws(key, "http://testserver/acme/new-order", nonce, {"identifiers": [{"type": "dns", "value": "own.com"}]}, kid=account_url), headers={"Content-Type": "application/jose+json"}).json()
    order_id = order["finalize"].split("/order/")[1].split("/finalize")[0]
    order_url = f"http://testserver/acme/order/{order_id}"
    order_path = f"/acme/order/{order_id}"

    key2, jwk2, account_url2 = _register_second_account(client)
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    resp = client.post(order_path, json=_jws(key2, order_url, nonce, None, kid=account_url2), headers={"Content-Type": "application/jose+json"})
    assert resp.status_code == 403
    assert "unauthorized" in resp.json()["type"]


def test_get_authz_cross_account_forbidden(client, db):
    """A second account cannot read another account's authorization."""
    key, jwk, account_url = _setup(client, db)
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    order = client.post("/acme/new-order", json=_jws(key, "http://testserver/acme/new-order", nonce, {"identifiers": [{"type": "dns", "value": "authzown.com"}]}, kid=account_url), headers={"Content-Type": "application/jose+json"}).json()
    authz_url = order["authorizations"][0]
    authz_path = "/acme" + authz_url.split("/acme", 1)[1]

    key2, jwk2, account_url2 = _register_second_account(client)
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    resp = client.post(authz_path, json=_jws(key2, authz_url, nonce, None, kid=account_url2), headers={"Content-Type": "application/jose+json"})
    assert resp.status_code == 403
    assert "unauthorized" in resp.json()["type"]


def test_respond_challenge_cross_account_forbidden(client, db):
    """A second account cannot trigger challenge validation for another account's authz."""
    key, jwk, account_url = _setup(client, db)
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    order = client.post("/acme/new-order", json=_jws(key, "http://testserver/acme/new-order", nonce, {"identifiers": [{"type": "dns", "value": "challown.com"}]}, kid=account_url), headers={"Content-Type": "application/jose+json"}).json()
    authz_id = order["authorizations"][0].split("/authz/")[1]
    chall_url = f"http://testserver/acme/challenge/{authz_id}/http-01"
    chall_path = f"/acme/challenge/{authz_id}/http-01"

    key2, jwk2, account_url2 = _register_second_account(client)
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    resp = client.post(chall_path, json=_jws(key2, chall_url, nonce, {}, kid=account_url2), headers={"Content-Type": "application/jose+json"})
    assert resp.status_code == 403
    assert "unauthorized" in resp.json()["type"]


def test_disabled_gate_get_order(client, db):
    """get_order returns 403 when ACME is disabled."""
    from app.models.setting import Setting
    from app.models import CertificateAuthority, CAType, User, UserRole
    from app.services.auth_service import AuthService
    from datetime import datetime, timezone
    db.add(Setting(key="acme_enabled", value="true"))
    db.add(Setting(key="acme_default_ca_id", value="ca-dis1"))
    auth = AuthService()
    user = User(username="dis_user1", email="dis1@test.com",
                password_hash=auth.hash_password("x"), role=UserRole.admin)
    db.add(user)
    db.flush()
    ca = CertificateAuthority(
        id="ca-dis1", name="Dis CA1", type=CAType.root,
        private_key_encrypted="test-key", certificate_pem="test-cert",
        key_algorithm="RSA", key_size=2048, subject_dn="CN=Dis CA1",
        serial_number="dis1",
        not_before=datetime.now(timezone.utc).replace(tzinfo=None),
        not_after=datetime.now(timezone.utc).replace(tzinfo=None),
        created_by=user.id,
    )
    db.add(ca)
    db.commit()
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = _rsa_jwk(key.public_key())
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    r = client.post("/acme/new-account", json=_jws(key, "http://testserver/acme/new-account", nonce, {"termsOfServiceAgreed": True}, jwk=jwk), headers={"Content-Type": "application/jose+json"})
    account_url = r.headers["Location"]
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    order = client.post("/acme/new-order", json=_jws(key, "http://testserver/acme/new-order", nonce, {"identifiers": [{"type": "dns", "value": "dis1.com"}]}, kid=account_url), headers={"Content-Type": "application/jose+json"}).json()
    order_id = order["finalize"].split("/order/")[1].split("/finalize")[0]

    # Disable ACME
    from app.models.setting import Setting as S
    setting = db.query(S).filter(S.key == "acme_enabled").first()
    setting.value = "false"
    db.commit()

    order_url = f"http://testserver/acme/order/{order_id}"
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    resp = client.post(f"/acme/order/{order_id}", json=_jws(key, order_url, nonce, None, kid=account_url), headers={"Content-Type": "application/jose+json"})
    assert resp.status_code == 403


def test_disabled_gate_get_authz(client, db):
    """get_authz returns 403 when ACME is disabled."""
    from app.models.setting import Setting
    from app.models import CertificateAuthority, CAType, User, UserRole
    from app.services.auth_service import AuthService
    from datetime import datetime, timezone
    db.add(Setting(key="acme_enabled", value="true"))
    db.add(Setting(key="acme_default_ca_id", value="ca-dis2"))
    auth = AuthService()
    user = User(username="dis_user2", email="dis2@test.com",
                password_hash=auth.hash_password("x"), role=UserRole.admin)
    db.add(user)
    db.flush()
    ca = CertificateAuthority(
        id="ca-dis2", name="Dis CA2", type=CAType.root,
        private_key_encrypted="test-key", certificate_pem="test-cert",
        key_algorithm="RSA", key_size=2048, subject_dn="CN=Dis CA2",
        serial_number="dis2",
        not_before=datetime.now(timezone.utc).replace(tzinfo=None),
        not_after=datetime.now(timezone.utc).replace(tzinfo=None),
        created_by=user.id,
    )
    db.add(ca)
    db.commit()
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = _rsa_jwk(key.public_key())
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    r = client.post("/acme/new-account", json=_jws(key, "http://testserver/acme/new-account", nonce, {"termsOfServiceAgreed": True}, jwk=jwk), headers={"Content-Type": "application/jose+json"})
    account_url = r.headers["Location"]
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    order = client.post("/acme/new-order", json=_jws(key, "http://testserver/acme/new-order", nonce, {"identifiers": [{"type": "dns", "value": "dis2.com"}]}, kid=account_url), headers={"Content-Type": "application/jose+json"}).json()
    authz_url = order["authorizations"][0]
    authz_path = "/acme" + authz_url.split("/acme", 1)[1]

    # Disable ACME
    from app.models.setting import Setting as S
    setting = db.query(S).filter(S.key == "acme_enabled").first()
    setting.value = "false"
    db.commit()

    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    resp = client.post(authz_path, json=_jws(key, authz_url, nonce, None, kid=account_url), headers={"Content-Type": "application/jose+json"})
    assert resp.status_code == 403


def test_disabled_gate_respond_challenge(client, db):
    """respond_challenge returns 403 when ACME is disabled."""
    from app.models.setting import Setting
    from app.models import CertificateAuthority, CAType, User, UserRole
    from app.services.auth_service import AuthService
    from datetime import datetime, timezone
    db.add(Setting(key="acme_enabled", value="true"))
    db.add(Setting(key="acme_default_ca_id", value="ca-dis3"))
    auth = AuthService()
    user = User(username="dis_user3", email="dis3@test.com",
                password_hash=auth.hash_password("x"), role=UserRole.admin)
    db.add(user)
    db.flush()
    ca = CertificateAuthority(
        id="ca-dis3", name="Dis CA3", type=CAType.root,
        private_key_encrypted="test-key", certificate_pem="test-cert",
        key_algorithm="RSA", key_size=2048, subject_dn="CN=Dis CA3",
        serial_number="dis3",
        not_before=datetime.now(timezone.utc).replace(tzinfo=None),
        not_after=datetime.now(timezone.utc).replace(tzinfo=None),
        created_by=user.id,
    )
    db.add(ca)
    db.commit()
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = _rsa_jwk(key.public_key())
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    r = client.post("/acme/new-account", json=_jws(key, "http://testserver/acme/new-account", nonce, {"termsOfServiceAgreed": True}, jwk=jwk), headers={"Content-Type": "application/jose+json"})
    account_url = r.headers["Location"]
    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    order = client.post("/acme/new-order", json=_jws(key, "http://testserver/acme/new-order", nonce, {"identifiers": [{"type": "dns", "value": "dis3.com"}]}, kid=account_url), headers={"Content-Type": "application/jose+json"}).json()
    authz_id = order["authorizations"][0].split("/authz/")[1]
    chall_url = f"http://testserver/acme/challenge/{authz_id}/http-01"

    # Disable ACME
    from app.models.setting import Setting as S
    setting = db.query(S).filter(S.key == "acme_enabled").first()
    setting.value = "false"
    db.commit()

    nonce = client.head("/acme/new-nonce").headers["Replay-Nonce"]
    resp = client.post(f"/acme/challenge/{authz_id}/http-01", json=_jws(key, chall_url, nonce, {}, kid=account_url), headers={"Content-Type": "application/jose+json"})
    assert resp.status_code == 403
