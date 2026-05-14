def test_dashboard_stats(client, admin_headers):
    response = client.get("/api/v1/dashboard/stats", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "active_cas" in data
    assert "active_certs" in data
    assert "pending_requests" in data
    assert "expiring_soon" in data


def test_dashboard_expiring(client, admin_headers):
    response = client.get("/api/v1/dashboard/expiring", headers=admin_headers)
    assert response.status_code == 200
    assert "items" in response.json()
