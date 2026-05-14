def test_login_success(client, admin_user):
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

def test_login_wrong_password(client, admin_user):
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401

def test_me_endpoint(client, admin_headers):
    response = client.get("/api/v1/auth/me", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["username"] == "admin"

def test_me_no_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401 or response.status_code == 403
