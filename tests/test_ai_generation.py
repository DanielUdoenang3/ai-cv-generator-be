import pytest


def test_ai_prompt_management_and_cv_generation_flow(client):
    # -----------------------------------------------------------------------
    # 1. Create Super Admin & Sub-Admin users
    # -----------------------------------------------------------------------
    resp = client.post(
        "/api/v1/admin/auth/create-admin",
        json={
            "first_name": "Super",
            "last_name": "Admin",
            "email": "super.ai@example.com",
            "password": "Password123!",
            "role": "super_admin",
        },
    )
    assert resp.status_code in [200, 201]

    login_resp = client.post(
        "/api/v1/admin/auth/login",
        json={"email": "super.ai@example.com", "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    super_data = login_resp.json()["data"]
    super_token = super_data["access_token"]
    super_headers = {"Authorization": f"Bearer {super_token}"}

    # Create Sub-Admin
    sub_admin_resp = client.post(
        "/api/v1/admin/auth/create-admin",
        json={
            "first_name": "Sarah",
            "last_name": "SubAdmin",
            "email": "sarah.sub@example.com",
            "password": "Password123!",
            "role": "sub_admin",
        },
        headers=super_headers,
    )
    assert sub_admin_resp.status_code in [200, 201]

    sub_login = client.post(
        "/api/v1/admin/auth/login",
        json={"email": "sarah.sub@example.com", "password": "Password123!"},
    )
    assert sub_login.status_code == 200
    sub_data = sub_login.json()["data"]
    sub_admin_id = sub_data["id"]
    sub_token = sub_data["access_token"]
    sub_headers = {"Authorization": f"Bearer {sub_token}"}

    # -----------------------------------------------------------------------
    # 2. Master System Prompt Management (Super Admin only)
    # -----------------------------------------------------------------------
    # Sub-admin should be rejected when listing prompts
    sub_list_prompts = client.get("/api/v1/admin/prompts", headers=sub_headers)
    assert sub_list_prompts.status_code == 403

    # Super Admin creates master prompt template
    create_prompt_resp = client.post(
        "/api/v1/admin/prompts",
        json={
            "name": "Senior Tech Lead Master Prompt v1",
            "content": "You are a master executive CV strategist. Generate a structured JSON CV for high-level technical roles.",
            "is_active": True,
        },
        headers=super_headers,
    )
    assert create_prompt_resp.status_code in [200, 201]
    prompt_data = create_prompt_resp.json()["data"]
    prompt_id = prompt_data["id"]
    assert prompt_data["is_active"] is True

    # List prompts as Super Admin
    list_prompts_resp = client.get("/api/v1/admin/prompts", headers=super_headers)
    assert list_prompts_resp.status_code == 200
    data = list_prompts_resp.json()["data"]
    assert "stats" in data
    assert "prompts" in data
    assert len(data["prompts"]) >= 1

    # -----------------------------------------------------------------------
    # 3. Client Submission & Chat Conversation Setup
    # -----------------------------------------------------------------------
    sub_create = client.post(
        "/api/v1/public/submissions",
        json={
            "first_name": "Robert",
            "last_name": "Kim",
            "email": "robert.kim@example.com",
            "target_position": "Backend Lead",
            "target_company": "TechCorp",
            "job_description": "Seeking a Backend Lead to scale API infrastructure.",
            "raw_data": {
                "education": [],
                "experience": [],
                "skills": ["Python", "FastAPI", "PostgreSQL"],
                "certifications": [],
                "custom_notes": "7 years backend experience with Python, FastAPI, and PostgreSQL.",
            },
        },
    )
    assert sub_create.status_code in [200, 201]
    sub_resp_data = sub_create.json()["data"]
    submission_id = sub_resp_data["submission_id"]
    client_token = sub_resp_data["access_token"]
    client_headers = {"X-Client-Access-Token": client_token}

    # Assign submission to Sub-Admin Sarah
    assign_resp = client.patch(
        f"/api/v1/admin/submissions/{submission_id}/assign",
        json={"assigned_to_id": sub_admin_id},
        headers=super_headers,
    )
    assert assign_resp.status_code == 200

    # Client sends chat message with key metrics (e.g. 40% latency reduction)
    chat_resp = client.post(
        f"/api/v1/public/submissions/{submission_id}/messages",
        headers=client_headers,
        data={"message": "I reduced API latency by 40% and handled 5 million requests per day at my last job."},
    )
    assert chat_resp.status_code in [200, 201]

    # -----------------------------------------------------------------------
    # 4. Trigger AI CV Generation Pipeline
    # -----------------------------------------------------------------------
    gen_resp = client.post(
        f"/api/v1/admin/submissions/{submission_id}/generate",
        json={
            "provider": "openai",
            "model": "gpt-4o",
            "custom_instructions": "Ensure heavy emphasis on the 40% latency reduction and 5M daily request metrics.",
            "include_chat_history": True,
        },
        headers=sub_headers,  # Sarah (assigned sub-admin) triggers generation
    )
    assert gen_resp.status_code == 200
    gen_data = gen_resp.json()["data"]

    assert "ai_generation_id" in gen_data
    assert gen_data["submission_id"] == submission_id
    assert gen_data["status"] == "success"
    assert "structured_cv" in gen_data

    cv = gen_data["structured_cv"]
    assert cv["personal_info"]["full_name"] == "Robert Kim"
    assert cv["personal_info"]["target_role"] == "Backend Lead"
    assert len(cv["work_experience"]) > 0
    assert "skills" in cv
    assert "education" in cv

    # -----------------------------------------------------------------------
    # 5. Verify Generation History Log
    # -----------------------------------------------------------------------
    log_resp = client.get(
        f"/api/v1/admin/submissions/{submission_id}/generations",
        headers=sub_headers,
    )
    assert log_resp.status_code == 200
    logs = log_resp.json()["data"]
    assert len(logs) == 1
    assert logs[0]["submission_id"] == submission_id
    assert logs[0]["status"] == "success"

    # -----------------------------------------------------------------------
    # 6. Verify Submission Status Escalate to Review
    # -----------------------------------------------------------------------
    sub_check = client.get(
        f"/api/v1/admin/submissions/{submission_id}",
        headers=sub_headers,
    )
    assert sub_check.status_code == 200
    assert sub_check.json()["data"]["status"] == "review"
