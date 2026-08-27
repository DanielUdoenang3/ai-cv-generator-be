import pytest


def setup_users(client):
    """Helper fixture setup for Super Admin and Sub-Admin headers."""
    # Create Super Admin
    client.post(
        "/api/v1/admin/auth/create-admin",
        json={
            "first_name": "Super",
            "last_name": "Admin",
            "email": "super.prompts@example.com",
            "password": "Password123!",
            "role": "super_admin",
        },
    )
    super_login = client.post(
        "/api/v1/admin/auth/login",
        json={"email": "super.prompts@example.com", "password": "Password123!"},
    )
    super_token = super_login.json()["data"]["access_token"]
    super_headers = {"Authorization": f"Bearer {super_token}"}

    # Create Sub-Admin
    client.post(
        "/api/v1/admin/auth/create-admin",
        json={
            "first_name": "Sub",
            "last_name": "Admin",
            "email": "sub.prompts@example.com",
            "password": "Password123!",
            "role": "sub_admin",
        },
        headers=super_headers,
    )
    sub_login = client.post(
        "/api/v1/admin/auth/login",
        json={"email": "sub.prompts@example.com", "password": "Password123!"},
    )
    sub_token = sub_login.json()["data"]["access_token"]
    sub_headers = {"Authorization": f"Bearer {sub_token}"}

    return super_headers, sub_headers


def test_prompt_seeding_and_stats(client):
    super_headers, _ = setup_users(client)

    # 1. Verify initial prompt seeding and stats
    res = client.get("/api/v1/admin/prompts", headers=super_headers)
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["stats"]["total_prompts"] == 4
    assert data["stats"]["active_prompts"] == 3
    assert data["stats"]["total_usage"] == 357

    prompts = data["prompts"]
    categories = [p["category"] for p in prompts]
    assert "Technology" in categories
    assert "Product" in categories
    assert "Executive" in categories
    assert "Marketing" in categories


def test_prompt_crud_activate_deactivate_duplicate(client):
    super_headers, _ = setup_users(client)

    # Get seeded prompts
    list_res = client.get("/api/v1/admin/prompts", headers=super_headers)
    prompts = list_res.json()["data"]["prompts"]
    mkt_prompt = next(p for p in prompts if p["category"] == "Marketing")
    swe_prompt = next(p for p in prompts if p["category"] == "Technology")

    # 1. Edit Prompt (PATCH /prompts/{id})
    edit_res = client.patch(
        f"/api/v1/admin/prompts/{mkt_prompt['id']}",
        json={
            "description": "Updated description for digital marketing leads",
            "category": "Growth Marketing",
        },
        headers=super_headers,
    )
    assert edit_res.status_code == 200
    assert edit_res.json()["data"]["description"] == "Updated description for digital marketing leads"
    assert edit_res.json()["data"]["category"] == "Growth Marketing"

    # 2. Activate Prompt (PATCH /prompts/{id}/activate)
    act_res = client.patch(
        f"/api/v1/admin/prompts/{mkt_prompt['id']}/activate",
        headers=super_headers,
    )
    assert act_res.status_code == 200
    assert act_res.json()["data"]["is_active"] is True

    # Check stats (active prompts count increased)
    check_act = client.get("/api/v1/admin/prompts", headers=super_headers)
    assert check_act.json()["data"]["stats"]["active_prompts"] == 4

    # 3. Deactivate Prompt (PATCH /prompts/{id}/deactivate)
    deact_res = client.patch(
        f"/api/v1/admin/prompts/{mkt_prompt['id']}/deactivate",
        headers=super_headers,
    )
    assert deact_res.status_code == 200
    assert deact_res.json()["data"]["is_active"] is False

    # Check stats (active prompts count decreased)
    check_deact = client.get("/api/v1/admin/prompts", headers=super_headers)
    assert check_deact.json()["data"]["stats"]["active_prompts"] == 3

    # 4. Duplicate Prompt (POST /prompts/{id}/duplicate)
    dup_res = client.post(
        f"/api/v1/admin/prompts/{swe_prompt['id']}/duplicate",
        headers=super_headers,
    )
    assert dup_res.status_code in [200, 201]
    dup_data = dup_res.json()["data"]
    assert dup_data["name"] == "Software Engineer CV (Copy)"
    assert dup_data["usage_count"] == 0

    # 5. Delete Prompt (DELETE /prompts/{id})
    del_res = client.delete(
        f"/api/v1/admin/prompts/{dup_data['id']}",
        headers=super_headers,
    )
    assert del_res.status_code == 200


def test_prompt_rbac_permissions(client):
    super_headers, sub_headers = setup_users(client)

    # Fetch valid prompt ID using Super Admin
    list_res = client.get("/api/v1/admin/prompts", headers=super_headers)
    prompt_id = list_res.json()["data"]["prompts"][0]["id"]

    # Sub-admin should be rejected with 403 Forbidden for all prompt endpoints
    assert client.get("/api/v1/admin/prompts", headers=sub_headers).status_code == 403
    assert client.post("/api/v1/admin/prompts", json={"name": "Test", "content": "123456789010"}, headers=sub_headers).status_code == 403
    assert client.patch(f"/api/v1/admin/prompts/{prompt_id}", json={"name": "Test"}, headers=sub_headers).status_code == 403
    assert client.patch(f"/api/v1/admin/prompts/{prompt_id}/activate", headers=sub_headers).status_code == 403
    assert client.patch(f"/api/v1/admin/prompts/{prompt_id}/deactivate", headers=sub_headers).status_code == 403
    assert client.post(f"/api/v1/admin/prompts/{prompt_id}/duplicate", headers=sub_headers).status_code == 403
    assert client.delete(f"/api/v1/admin/prompts/{prompt_id}", headers=sub_headers).status_code == 403

    # Unauthenticated requests should be rejected with 401 Unauthorized
    assert client.get("/api/v1/admin/prompts").status_code == 401


def test_prompt_not_found_and_validation_errors(client):
    super_headers, _ = setup_users(client)
    fake_id = "non-existent-prompt-id-999"

    # 404 Not Found tests
    assert client.patch(f"/api/v1/admin/prompts/{fake_id}", json={"name": "Test"}, headers=super_headers).status_code == 404
    assert client.patch(f"/api/v1/admin/prompts/{fake_id}/activate", headers=super_headers).status_code == 404
    assert client.patch(f"/api/v1/admin/prompts/{fake_id}/deactivate", headers=super_headers).status_code == 404
    assert client.post(f"/api/v1/admin/prompts/{fake_id}/duplicate", headers=super_headers).status_code == 404
    assert client.delete(f"/api/v1/admin/prompts/{fake_id}", headers=super_headers).status_code == 404

    # 422 Validation Error tests
    # Content too short (< 10 chars)
    invalid_create = client.post(
        "/api/v1/admin/prompts",
        json={"name": "Short Prompt", "content": "Short"},
        headers=super_headers,
    )
    assert invalid_create.status_code == 422


def test_smart_prompt_matching_and_usage_counter(client):
    super_headers, _ = setup_users(client)

    # Create submission for a Product Manager
    sub_pm = client.post(
        "/api/v1/public/submissions",
        json={
            "first_name": "Jessica",
            "last_name": "Product",
            "email": "jessica.pm@example.com",
            "target_position": "Senior Product Manager",
            "job_description": "Leading cross-functional product launches.",
            "raw_data": {"skills": ["Roadmap", "Agile"]},
        },
    )
    pm_sub_id = sub_pm.json()["data"]["submission_id"]

    # Trigger generation for Product Manager
    gen_pm = client.post(
        f"/api/v1/admin/submissions/{pm_sub_id}/generate",
        json={"provider": "openai", "model": "gpt-4o"},
        headers=super_headers,
    )
    assert gen_pm.status_code == 200

    # Verify Product Manager CV prompt usage count increased by 1 (89 -> 90)
    prompts_after = client.get("/api/v1/admin/prompts", headers=super_headers).json()["data"]["prompts"]
    pm_prompt = next(p for p in prompts_after if p["name"] == "Product Manager CV")
    assert pm_prompt["usage_count"] == 90

    # Submission matching deactivated category (Marketing) should fall back to an active prompt
    sub_mkt = client.post(
        "/api/v1/public/submissions",
        json={
            "first_name": "Mark",
            "last_name": "Growth",
            "email": "mark.growth@example.com",
            "target_position": "Digital Marketing Lead",
            "job_description": "Running SEO and PPC campaigns.",
            "raw_data": {"skills": ["SEO", "PPC"]},
        },
    )
    mkt_sub_id = sub_mkt.json()["data"]["submission_id"]

    gen_mkt = client.post(
        f"/api/v1/admin/submissions/{mkt_sub_id}/generate",
        json={"provider": "openai", "model": "gpt-4o"},
        headers=super_headers,
    )
    assert gen_mkt.status_code == 200

    # Test expanded role keywords: Cybersecurity Architect -> Technology
    sub_cyber = client.post(
        "/api/v1/public/submissions",
        json={
            "first_name": "Dave",
            "last_name": "Sec",
            "email": "dave.sec@example.com",
            "target_position": "Cybersecurity Architect & DevOps Specialist",
            "job_description": "Securing cloud workloads.",
            "raw_data": {"skills": ["Security", "Kubernetes"]},
        },
    )
    cyber_sub_id = sub_cyber.json()["data"]["submission_id"]
    gen_cyber = client.post(
        f"/api/v1/admin/submissions/{cyber_sub_id}/generate",
        json={"provider": "openai", "model": "gpt-4o"},
        headers=super_headers,
    )
    assert gen_cyber.status_code == 200

    # Test dynamic custom prompt category matching (e.g. Finance)
    create_fin_res = client.post(
        "/api/v1/admin/prompts",
        json={
            "name": "Financial Analyst Master Prompt",
            "description": "Tailored for finance, accounting, and investment roles",
            "category": "Finance",
            "content": "You are a Wall Street financial executive strategist. Build structured CVs.",
            "is_active": True,
        },
        headers=super_headers,
    )
    assert create_fin_res.status_code in [200, 201]

    sub_fin = client.post(
        "/api/v1/public/submissions",
        json={
            "first_name": "Elena",
            "last_name": "Finance",
            "email": "elena.finance@example.com",
            "target_position": "Senior Finance Analyst",
            "job_description": "Financial modeling and auditing.",
            "raw_data": {"skills": ["Financial Modeling", "Excel"]},
        },
    )
    fin_sub_id = sub_fin.json()["data"]["submission_id"]
    gen_fin = client.post(
        f"/api/v1/admin/submissions/{fin_sub_id}/generate",
        json={"provider": "openai", "model": "gpt-4o"},
        headers=super_headers,
    )
    assert gen_fin.status_code == 200

    # Verify custom Finance prompt usage count increased from 0 to 1
    prompts_final = client.get("/api/v1/admin/prompts", headers=super_headers).json()["data"]["prompts"]
    fin_prompt = next(p for p in prompts_final if p["name"] == "Financial Analyst Master Prompt")
    assert fin_prompt["usage_count"] == 1
