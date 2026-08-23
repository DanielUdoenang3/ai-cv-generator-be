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


def test_admin_update_profile(client):
    # 1. Create and login admin
    client.post("/api/v1/admin/auth/create-admin", json={
        "first_name": "OldName",
        "last_name": "OldLast",
        "email": "oldprofile@example.com",
        "password": "Password123!",
        "role": "sub_admin"
    })
    login_res = client.post("/api/v1/admin/auth/login", json={
        "email": "oldprofile@example.com",
        "password": "Password123!"
    })
    headers = {"Authorization": f"Bearer {login_res.json()['data']['access_token']}"}

    # 2. Update profile (name, phone, gender)
    res_update = client.put(
        "/api/v1/admin/auth/profile",
        headers=headers,
        json={
            "first_name": "NewName",
            "last_name": "NewLast",
            "phone": "+2348000000",
            "gender": "male"
        }
    )
    assert res_update.status_code == 200
    update_data = res_update.json()["data"]
    assert update_data["first_name"] == "NewName"
    assert update_data["last_name"] == "NewLast"
    assert update_data["phone"] == "+2348000000"
    assert update_data["gender"] == "male"
    assert update_data["role"] == "sub_admin"  # Role must not change!

    # 3. Update email (success)
    res_email = client.put(
        "/api/v1/admin/auth/profile",
        headers=headers,
        json={"email": "newprofile@example.com"}
    )
    assert res_email.status_code == 200
    email_data = res_email.json()["data"]
    assert email_data["email"] == "newprofile@example.com"
    assert "access_token" in email_data
    
    # Use the new token for subsequent requests
    headers = {"Authorization": f"Bearer {email_data['access_token']}"}

    # 4. Try updating email to an existing one (should fail)
    client.post("/api/v1/admin/auth/create-admin", json={
        "first_name": "Another",
        "last_name": "Admin",
        "email": "taken@example.com",
        "password": "Password123!",
        "role": "sub_admin"
    })
    res_fail = client.put(
        "/api/v1/admin/auth/profile",
        headers=headers,
        json={"email": "taken@example.com"}
    )
    assert res_fail.status_code == 400
    assert "already taken" in res_fail.json()["detail"]["message"]

