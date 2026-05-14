def test_audit_log_created_on_login(client, admin_user):
    client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    response = client.get("/api/v1/audit/logs", headers=_get_admin_headers(client))
    assert response.status_code == 200
    logs = response.json()["items"]
    assert any(log["action"] == "login" for log in logs)

def _get_admin_headers(client):
    resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
