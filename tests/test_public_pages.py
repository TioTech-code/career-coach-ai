def test_homepage_loads(client):
    response = client.get("/")

    assert response.status_code == 200


def test_login_page_loads(client):
    response = client.get("/login")

    assert response.status_code == 200


def test_register_page_loads(client):
    response = client.get("/register")

    assert response.status_code == 200