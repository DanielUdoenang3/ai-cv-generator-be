"""
Tests for PATCH /api/v1/admin/submissions/{submission_id}/resume-text

Covers:
- Happy path: super admin saves resume text
- Happy path: assigned sub-admin saves resume text
- Persists text and creates audit activity
- 404 on non-existent submission
- Sub-admin blocked on unassigned submission (403)
- Empty / whitespace-only text rejected (422 from schema validation)
- Unauthenticated request returns 401
- Overwrite: second save replaces the first value
"""

# ── helpers ──────────────────────────────────────────────────────────────────

def _create_super_admin(client, email="resume.super@example.com"):
    client.post("/api/v1/admin/auth/create-admin", json={
        "first_name": "Super", "last_name": "Admin",
        "email": email, "password": "Password123!", "role": "super_admin",
    })
    resp = client.post("/api/v1/admin/auth/login",
                       json={"email": email, "password": "Password123!"})
    data = resp.json()["data"]
    return {"Authorization": f"Bearer {data['access_token']}"}, data["id"]


def _create_sub_admin(client, email="resume.sub@example.com"):
    client.post("/api/v1/admin/auth/create-admin", json={
        "first_name": "Sub", "last_name": "Admin",
        "email": email, "password": "Password123!", "role": "sub_admin",
    })
    resp = client.post("/api/v1/admin/auth/login",
                       json={"email": email, "password": "Password123!"})
    data = resp.json()["data"]
    return {"Authorization": f"Bearer {data['access_token']}"}, data["id"]


def _create_submission(client, email="resume.client@example.com"):
    resp = client.post("/api/v1/public/submissions", json={
        "first_name": "Jane", "last_name": "Doe",
        "email": email, "target_position": "Software Engineer",
        "raw_data": {"education": [], "experience": [], "skills": [], "certifications": []},
    })
    return resp.json()["data"]["submission_id"]


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_super_admin_saves_resume_text(client):
    """Super admin can save resume text; response contains the saved text."""
    super_headers, _ = _create_super_admin(client)
    sub_id = _create_submission(client)

    resume = "5+ years Python engineer. Led API infra at Stripe. Reduced P99 latency by 40%."
    resp = client.patch(
        f"/api/v1/admin/submissions/{sub_id}/resume-text",
        headers=super_headers,
        json={"saved_resume_text": resume},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["data"]["submission_id"] == sub_id
    assert data["data"]["saved_resume_text"] == resume


def test_assigned_sub_admin_saves_resume_text(client):
    """Sub-admin assigned to a submission can save resume text successfully."""
    super_headers, _ = _create_super_admin(client)
    sub_headers, sub_id = _create_sub_admin(client)
    submission_id = _create_submission(client)

    # Assign the submission to the sub-admin
    client.patch(
        f"/api/v1/admin/submissions/{submission_id}/assign",
        headers=super_headers,
        json={"assigned_to_id": sub_id},
    )

    resume = "Experienced product manager with 7 years building B2B SaaS."
    resp = client.patch(
        f"/api/v1/admin/submissions/{submission_id}/resume-text",
        headers=sub_headers,
        json={"saved_resume_text": resume},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["saved_resume_text"] == resume


def test_save_resume_text_persists_in_submission(client):
    """After saving, the text is readable back via GET /submissions/{id}."""
    super_headers, _ = _create_super_admin(client)
    sub_id = _create_submission(client)

    resume = "Cloud architect with AWS and Kubernetes expertise."
    client.patch(
        f"/api/v1/admin/submissions/{sub_id}/resume-text",
        headers=super_headers,
        json={"saved_resume_text": resume},
    )

    # Verify it is persisted
    get_resp = client.get(f"/api/v1/admin/submissions/{sub_id}", headers=super_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["saved_resume_text"] == resume


def test_save_resume_text_creates_audit_activity(client):
    """Saving resume text creates a 'resume_text_saved' activity in the timeline."""
    super_headers, _ = _create_super_admin(client)
    sub_id = _create_submission(client)

    client.patch(
        f"/api/v1/admin/submissions/{sub_id}/resume-text",
        headers=super_headers,
        json={"saved_resume_text": "Full-stack developer with React and Node.js."},
    )

    get_resp = client.get(f"/api/v1/admin/submissions/{sub_id}", headers=super_headers)
    activities = get_resp.json()["data"]["activities"]
    resume_acts = [a for a in activities if a["activity_type"] == "resume_text_saved"]
    assert len(resume_acts) == 1
    assert "Resume Text Saved" in resume_acts[0]["title"]


def test_save_resume_text_overwrite(client):
    """Saving again replaces the previous value — latest value wins."""
    super_headers, _ = _create_super_admin(client)
    sub_id = _create_submission(client)

    client.patch(
        f"/api/v1/admin/submissions/{sub_id}/resume-text",
        headers=super_headers,
        json={"saved_resume_text": "First version of resume text."},
    )
    client.patch(
        f"/api/v1/admin/submissions/{sub_id}/resume-text",
        headers=super_headers,
        json={"saved_resume_text": "Updated version with new metrics."},
    )

    get_resp = client.get(f"/api/v1/admin/submissions/{sub_id}", headers=super_headers)
    assert get_resp.json()["data"]["saved_resume_text"] == "Updated version with new metrics."


def test_save_resume_text_404_unknown_submission(client):
    """Returns 404 when submission_id does not exist."""
    super_headers, _ = _create_super_admin(client)
    resp = client.patch(
        "/api/v1/admin/submissions/nonexistent-sub-id/resume-text",
        headers=super_headers,
        json={"saved_resume_text": "Some resume text."},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]["message"].lower()


def test_save_resume_text_403_unassigned_sub_admin(client):
    """Sub-admin cannot save resume text for a submission not assigned to them."""
    super_headers, _ = _create_super_admin(client)
    sub_headers, _ = _create_sub_admin(client)
    submission_id = _create_submission(client)

    # Deliberately do NOT assign to the sub-admin
    resp = client.patch(
        f"/api/v1/admin/submissions/{submission_id}/resume-text",
        headers=sub_headers,
        json={"saved_resume_text": "Unauthorized resume text."},
    )
    assert resp.status_code == 403
    assert "not assigned" in resp.json()["detail"]["message"].lower()


def test_save_resume_text_401_unauthenticated(client):
    """Unauthenticated request returns 401."""
    sub_id = _create_submission(client)
    resp = client.patch(
        f"/api/v1/admin/submissions/{sub_id}/resume-text",
        json={"saved_resume_text": "No auth."},
    )
    assert resp.status_code == 401


def test_save_resume_text_422_empty_string(client):
    """Sending an empty string fails schema validation (min_length=1)."""
    super_headers, _ = _create_super_admin(client)
    sub_id = _create_submission(client)

    resp = client.patch(
        f"/api/v1/admin/submissions/{sub_id}/resume-text",
        headers=super_headers,
        json={"saved_resume_text": ""},
    )
    assert resp.status_code == 422


def test_save_resume_text_422_missing_field(client):
    """Omitting the required field fails validation with 422."""
    super_headers, _ = _create_super_admin(client)
    sub_id = _create_submission(client)

    resp = client.patch(
        f"/api/v1/admin/submissions/{sub_id}/resume-text",
        headers=super_headers,
        json={},
    )
    assert resp.status_code == 422
