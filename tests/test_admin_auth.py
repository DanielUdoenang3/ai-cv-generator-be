def test_admin_create_and_login_flow(client):
    create_payload = {
        "first_name": "Admin",
        "last_name": "User",
        "email": "admin@example.com",
        "password": "SecurePassword123!",
        "role": "super_admin"
    }

    res = client.post("/api/v1/admin/auth/create-admin", json=create_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status_code"] == 201
    assert data["data"]["email"] == "admin@example.com"

    login_payload = {
        "email": "admin@example.com",
        "password": "SecurePassword123!"
    }
    res_login = client.post("/api/v1/admin/auth/login", json=login_payload)
    assert res_login.status_code == 200
    login_data = res_login.json()
    assert login_data["status_code"] == 200
    assert "access_token" in login_data["data"]

    token = login_data["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res_profile = client.get("/api/v1/admin/auth/profile", headers=headers)
    assert res_profile.status_code == 200
    profile_data = res_profile.json()
    assert profile_data["data"]["email"] == "admin@example.com"


def test_admin_login_invalid_password(client):
    client.post("/api/v1/admin/auth/create-admin", json={
        "first_name": "Staff",
        "last_name": "Member",
        "email": "staff@example.com",
        "password": "CorrectPassword123!",
        "role": "sub_admin"
    })

    res = client.post("/api/v1/admin/auth/login", json={
        "email": "staff@example.com",
        "password": "WrongPassword!"
    })
    assert res.status_code == 401
    assert res.json()["detail"]["message"] == "Invalid credentials"


def test_admin_profile_unauthorized(client):
    res = client.get("/api/v1/admin/auth/profile", headers={"Authorization": "Bearer invalid.jwt.token"})
    assert res.status_code == 401
