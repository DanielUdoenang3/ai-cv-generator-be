def _setup_admin_and_submission(client):
    # 1. Create Super Admin
    client.post("/api/v1/admin/auth/create-admin", json={
        "first_name": "Super",
        "last_name": "Admin",
        "email": "superadmin@example.com",
        "password": "Password123!",
        "role": "super_admin"
    })
    login_res = client.post("/api/v1/admin/auth/login", json={
        "email": "superadmin@example.com",
        "password": "Password123!"
    })
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Public Submission
    sub_res = client.post("/api/v1/public/submissions", json={
        "first_name": "Bob",
        "last_name": "Builder",
        "email": "bob@example.com",
        "target_position": "Architect",
        "raw_data": {"education": [], "experience": [], "skills": [], "certifications": []}
    })
    sub_id = sub_res.json()["data"]["submission_id"]

    return headers, sub_id


def test_admin_get_all_submissions(client):
    headers, _ = _setup_admin_and_submission(client)

    res = client.get("/api/v1/admin/submissions", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status_code"] == 200
    assert len(data["data"]["submissions"]) >= 1


def test_admin_get_single_submission(client):
    headers, sub_id = _setup_admin_and_submission(client)

    res = client.get(f"/api/v1/admin/submissions/{sub_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status_code"] == 200
    assert data["data"]["id"] == sub_id


def test_admin_update_submission_status(client):
    headers, sub_id = _setup_admin_and_submission(client)

    res = client.patch(
        f"/api/v1/admin/submissions/{sub_id}/status",
        headers=headers,
        json={"status": "in_progress"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status_code"] == 200
    assert data["data"]["status"] == "in_progress"


def test_admin_send_chat_message(client):
    headers, sub_id = _setup_admin_and_submission(client)

    res = client.post(
        f"/api/v1/admin/submissions/{sub_id}/messages",
        headers=headers,
        data={"message": "Hello Bob, we have started working on your CV draft."}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status_code"] == 201
    assert data["data"]["sender_type"] == "staff"
    assert data["data"]["message"] == "Hello Bob, we have started working on your CV draft."
