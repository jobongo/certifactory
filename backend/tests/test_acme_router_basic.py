def _enable_acme(db, ca_id="some-ca"):
    from app.models.setting import Setting
    db.add(Setting(key="acme_enabled", value="true"))
    db.add(Setting(key="acme_default_ca_id", value=ca_id))
    db.commit()


def test_directory_returns_endpoints(client, db):
    _enable_acme(db)
    resp = client.get("/acme/directory")
    assert resp.status_code == 200
    body = resp.json()
    assert body["newNonce"].endswith("/acme/new-nonce")
    assert "newAccount" in body
    assert "newOrder" in body


def test_directory_disabled_returns_403(client, db):
    resp = client.get("/acme/directory")
    assert resp.status_code == 403


def test_new_nonce_returns_replay_nonce_header(client, db):
    _enable_acme(db)
    resp = client.head("/acme/new-nonce")
    assert resp.status_code == 200
    assert "Replay-Nonce" in resp.headers
