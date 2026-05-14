def test_create_root_ca(client, admin_headers):
    response = client.post(
        "/api/v1/cas",
        json={
            "name": "Test Root CA",
            "subject": {"CN": "Test Root CA", "O": "TestOrg", "C": "US"},
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 3650,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Root CA"
    assert data["type"] == "root"
    assert data["status"] == "active"


def test_create_intermediate_ca(client, admin_headers):
    root = client.post(
        "/api/v1/cas",
        json={
            "name": "Root CA",
            "subject": {"CN": "Root CA", "O": "Test", "C": "US"},
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 3650,
        },
        headers=admin_headers,
    ).json()

    response = client.post(
        f"/api/v1/cas/{root['id']}/intermediate",
        json={
            "name": "Intermediate CA",
            "subject": {"CN": "Intermediate CA", "O": "Test", "C": "US"},
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 1825,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "intermediate"
    assert data["parent_ca_id"] == root["id"]


def test_list_cas(client, admin_headers):
    client.post(
        "/api/v1/cas",
        json={
            "name": "CA1",
            "subject": {"CN": "CA1", "O": "Test", "C": "US"},
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 3650,
        },
        headers=admin_headers,
    )
    response = client.get("/api/v1/cas", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_get_ca_tree(client, admin_headers):
    root = client.post(
        "/api/v1/cas",
        json={
            "name": "Root",
            "subject": {"CN": "Root", "O": "Test", "C": "US"},
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 3650,
        },
        headers=admin_headers,
    ).json()
    client.post(
        f"/api/v1/cas/{root['id']}/intermediate",
        json={
            "name": "Child",
            "subject": {"CN": "Child", "O": "Test", "C": "US"},
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 1825,
        },
        headers=admin_headers,
    )
    response = client.get("/api/v1/cas/tree", headers=admin_headers)
    assert response.status_code == 200
    tree = response.json()
    assert len(tree) >= 1
    assert len(tree[0]["children"]) >= 1


def test_disable_ca(client, admin_headers):
    ca = client.post(
        "/api/v1/cas",
        json={
            "name": "DisableMe",
            "subject": {"CN": "DisableMe", "O": "Test", "C": "US"},
            "key_algorithm": "RSA",
            "key_size": 2048,
            "validity_days": 3650,
        },
        headers=admin_headers,
    ).json()
    response = client.post(f"/api/v1/cas/{ca['id']}/disable", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "disabled"
