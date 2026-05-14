def test_create_user(client, admin_headers):
    response = client.post("/api/v1/users", json={"username": "operator1", "email": "op@test.com", "password": "pass123", "role": "operator"}, headers=admin_headers)
    assert response.status_code == 201
    assert response.json()["username"] == "operator1"
    assert response.json()["role"] == "operator"

def test_list_users(client, admin_headers, admin_user):
    response = client.get("/api/v1/users", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["total"] >= 1

def test_get_user(client, admin_headers, admin_user):
    response = client.get(f"/api/v1/users/{admin_user.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["username"] == "admin"

def test_update_user(client, admin_headers, admin_user):
    response = client.put(f"/api/v1/users/{admin_user.id}", json={"role": "operator"}, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["role"] == "operator"

def test_non_admin_cannot_create_user(client, db):
    from app.models import User, UserRole
    from app.services.auth_service import AuthService
    auth = AuthService()
    user = User(username="requester1", email="req@test.com", password_hash=auth.hash_password("pass123"), role=UserRole.requester)
    db.add(user)
    db.commit()
    token = auth.create_access_token(user.id, user.role.value)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/users", json={"username": "newuser", "email": "new@test.com", "password": "pass123", "role": "requester"}, headers=headers)
    assert response.status_code == 403
