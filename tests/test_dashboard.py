def test_dashboard_requires_login(client):

    response = client.get("/dashboard")

    assert response.status_code == 302