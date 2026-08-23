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


def test_admin_get_all_submissions_with_filters(client):
    # 1. Create Super Admin
    client.post("/api/v1/admin/auth/create-admin", json={
        "first_name": "Filter",
        "last_name": "Admin",
        "email": "filteradmin@example.com",
        "password": "Password123!",
        "role": "super_admin"
    })
    login_res = client.post("/api/v1/admin/auth/login", json={
        "email": "filteradmin@example.com",
        "password": "Password123!"
    })
    headers = {"Authorization": f"Bearer {login_res.json()['data']['access_token']}"}

    # 2. Create multiple submissions with different characteristics
    # Sub1
    client.post("/api/v1/public/submissions", json={
        "first_name": "Alex",
        "last_name": "Backend",
        "email": "alex@example.com",
        "target_position": "Backend Developer",
        "target_company": "Stripe",
        "priority": "high",
        "raw_data": {"education": [], "experience": [], "skills": [], "certifications": []}
    })
    # Sub2
    client.post("/api/v1/public/submissions", json={
        "first_name": "Betty",
        "last_name": "Frontend",
        "email": "betty@example.com",
        "target_position": "Frontend Engineer",
        "target_company": "Vercel",
        "priority": "normal",
        "raw_data": {"education": [], "experience": [], "skills": [], "certifications": []}
    })

    # Test Search (by name)
    res_search = client.get("/api/v1/admin/submissions?search=Alex", headers=headers)
    assert res_search.status_code == 200
    data_search = res_search.json()["data"]
    assert data_search["total"] == 1
    assert data_search["submissions"][0]["client"]["first_name"] == "Alex"

    # Test Search (by company)
    res_search_company = client.get("/api/v1/admin/submissions?search=Vercel", headers=headers)
    assert res_search_company.status_code == 200
    data_search_company = res_search_company.json()["data"]
    assert data_search_company["total"] == 1
    assert data_search_company["submissions"][0]["client"]["first_name"] == "Betty"

    # Test Search (by reference ID)
    ref_id = data_search_company["submissions"][0]["reference_id"]
    res_search_ref = client.get(f"/api/v1/admin/submissions?search={ref_id}", headers=headers)
    assert res_search_ref.status_code == 200
    data_search_ref = res_search_ref.json()["data"]
    assert data_search_ref["total"] == 1

    # Test Pagination (limit=1)
    res_paginated = client.get("/api/v1/admin/submissions?limit=1&page=1", headers=headers)
    assert res_paginated.status_code == 200
    data_pag = res_paginated.json()["data"]
    assert data_pag["limit"] == 1
    assert len(data_pag["submissions"]) == 1
    assert data_pag["total"] >= 2


def test_admin_unassign_submission(client):
    # 1. Create and login Super Admin
    client.post("/api/v1/admin/auth/create-admin", json={
        "first_name": "Super",
        "last_name": "Boss",
        "email": "superbossunassign@example.com",
        "password": "Password123!",
        "role": "super_admin"
    })
    login_super = client.post("/api/v1/admin/auth/login", json={
        "email": "superbossunassign@example.com",
        "password": "Password123!"
    })
    super_headers = {"Authorization": f"Bearer {login_super.json()['data']['access_token']}"}

    # 2. Create a Sub Admin via staff API
    res_staff = client.post(
        "/api/v1/admin/staff",
        headers=super_headers,
        json={
            "first_name": "David",
            "last_name": "Staff",
            "email": "davidstaff@example.com",
            "password": "Password123!",
            "role": "sub_admin",
            "phone": "+12345678",
            "gender": "male"
        }
    )
    staff_id = res_staff.json()["data"]["id"]

    # 3. Create a public submission
    res_sub = client.post("/api/v1/public/submissions", json={
        "first_name": "Client",
        "last_name": "Name",
        "email": "client@example.com",
        "target_position": "Developer",
        "raw_data": {"education": [], "experience": [], "skills": []}
    })
    sub_id = res_sub.json()["data"]["submission_id"]

    # 4. Assign submission to David
    client.patch(
        f"/api/v1/admin/submissions/{sub_id}/assign",
        headers=super_headers,
        json={"assigned_to_id": staff_id}
    )

    # Verify assignment is active
    res_verify = client.get(f"/api/v1/admin/submissions/{sub_id}", headers=super_headers)
    assert res_verify.json()["data"]["assigned_to"]["id"] == staff_id

    # 5. Call unassign endpoint
    res_unassign = client.patch(
        f"/api/v1/admin/submissions/{sub_id}/unassign",
        headers=super_headers
    )
    assert res_unassign.status_code == 200
    assert res_unassign.json()["data"]["assigned_to"] is None

    # 6. Verify audit activity log is created
    res_details = client.get(f"/api/v1/admin/submissions/{sub_id}", headers=super_headers)
    activities = res_details.json()["data"]["activities"]
    unassign_act = next(
        a for a in activities
        if a["activity_type"] == "assigned" and "unassigned from this submission" in a["description"]
    )
    assert unassign_act is not None

