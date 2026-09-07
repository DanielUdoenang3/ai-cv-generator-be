"""
Tests for PATCH /api/v1/admin/submissions/{submission_id}/job-description

Covers:
- Super admin sets a job description
- Assigned sub-admin sets a job description
- Clearing the field (null / empty string → stored as None)
- Persists and is visible on GET /submissions/{id}
- Creates an audit activity on update and on clear
- 404 on non-existent submission
- 403 for sub-admin on unassigned submission
- 401 for unauthenticated requests
"""


# ── helpers ───────────────────────────────────────────────────────────────────

def _create_super_admin(client, email="jd.super@example.com"):
    client.post("/api/v1/admin/auth/create-admin", json={
        "first_name": "Super", "last_name": "Boss",
        "email": email, "password": "Password123!", "role": "super_admin",
    })
    resp = client.post("/api/v1/admin/auth/login",
                       json={"email": email, "password": "Password123!"})
    data = resp.json()["data"]
    return {"Authorization": f"Bearer {data['access_token']}"}, data["id"]


def _create_sub_admin(client, email="jd.sub@example.com"):
    client.post("/api/v1/admin/auth/create-admin", json={
        "first_name": "Sub", "last_name": "Worker",
        "email": email, "password": "Password123!", "role": "sub_admin",
    })
    resp = client.post("/api/v1/admin/auth/login",
                       json={"email": email, "password": "Password123!"})
    data = resp.json()["data"]
    return {"Authorization": f"Bearer {data['access_token']}"}, data["id"]


def _create_submission(client, email="jd.client@example.com"):
    resp = client.post("/api/v1/public/submissions", json={
        "first_name": "Tom", "last_name": "Smith",
        "email": email, "target_position": "Product Manager",
        "raw_data": {"education": [], "experience": [], "skills": [], "certifications": []},
    })
    return resp.json()["data"]["submission_id"]


JD_TEXT = (
    "We are looking for a Senior Product Manager to lead our B2B SaaS roadmap. "
    "You will own the full product lifecycle from discovery to launch, "
    "working closely with engineering, design, and sales."
)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_super_admin_sets_job_description(client):
    """Super admin can set a job description on any submission."""
    super_headers, _ = _create_super_admin(client)
    sub_id = _create_submission(client)

    resp = client.patch(
        f"/api/v1/admin/submissions/{sub_id}/job-description",
        headers=super_headers,
        json={"job_description": JD_TEXT},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["data"]["submission_id"] == sub_id
    assert data["data"]["job_description"] == JD_TEXT


def test_assigned_sub_admin_sets_job_description(client):
    """An assigned sub-admin can update the job description."""
    super_headers, _ = _create_super_admin(client)
    sub_headers, sub_id = _create_sub_admin(client)
    submission_id = _create_submission(client)

    client.patch(
        f"/api/v1/admin/submissions/{submission_id}/assign",
        headers=super_headers,
        json={"assigned_to_id": sub_id},
    )

    resp = client.patch(
        f"/api/v1/admin/submissions/{submission_id}/job-description",
        headers=sub_headers,
        json={"job_description": JD_TEXT},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["job_description"] == JD_TEXT


def test_job_description_persists_in_submission(client):
    """After setting, job_description is readable via GET /submissions/{id}."""
    super_headers, _ = _create_super_admin(client)
    sub_id = _create_submission(client)

    client.patch(
        f"/api/v1/admin/submissions/{sub_id}/job-description",
        headers=super_headers,
        json={"job_description": JD_TEXT},
    )

    get_resp = client.get(f"/api/v1/admin/submissions/{sub_id}", headers=super_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["job_description"] == JD_TEXT


def test_clear_job_description_with_null(client):
    """Passing null clears the field (stored as None) and logs 'cleared' activity."""
    super_headers, _ = _create_super_admin(client)
    sub_id = _create_submission(client)

    # First set it
    client.patch(
        f"/api/v1/admin/submissions/{sub_id}/job-description",
        headers=super_headers,
        json={"job_description": JD_TEXT},
    )

    # Then clear it
    resp = client.patch(
        f"/api/v1/admin/submissions/{sub_id}/job-description",
        headers=super_headers,
        json={"job_description": None},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["job_description"] is None
    assert "cleared" in resp.json()["message"].lower()


def test_clear_job_description_with_empty_string(client):
    """Passing an empty string also clears the field."""
    super_headers, _ = _create_super_admin(client)
    sub_id = _create_submission(client)

    client.patch(
        f"/api/v1/admin/submissions/{sub_id}/job-description",
        headers=super_headers,
        json={"job_description": JD_TEXT},
    )

    resp = client.patch(
        f"/api/v1/admin/submissions/{sub_id}/job-description",
        headers=super_headers,
        json={"job_description": ""},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["job_description"] is None


def test_update_job_description_creates_audit_activity(client):
    """Updating the JD creates a 'job_description_updated' activity in the timeline."""
    super_headers, _ = _create_super_admin(client)
    sub_id = _create_submission(client)

    client.patch(
        f"/api/v1/admin/submissions/{sub_id}/job-description",
        headers=super_headers,
        json={"job_description": JD_TEXT},
    )

    get_resp = client.get(f"/api/v1/admin/submissions/{sub_id}", headers=super_headers)
    activities = get_resp.json()["data"]["activities"]
    jd_acts = [a for a in activities if a["activity_type"] == "job_description_updated"]
    assert len(jd_acts) >= 1
    assert "updated" in jd_acts[0]["title"].lower() or "Updated" in jd_acts[0]["title"]


def test_clear_job_description_creates_cleared_activity(client):
    """Clearing the JD creates an activity with 'Cleared' in the title."""
    super_headers, _ = _create_super_admin(client)
    sub_id = _create_submission(client)

    client.patch(
        f"/api/v1/admin/submissions/{sub_id}/job-description",
        headers=super_headers,
        json={"job_description": JD_TEXT},
    )
    client.patch(
        f"/api/v1/admin/submissions/{sub_id}/job-description",
        headers=super_headers,
        json={"job_description": None},
    )

    get_resp = client.get(f"/api/v1/admin/submissions/{sub_id}", headers=super_headers)
    activities = get_resp.json()["data"]["activities"]
    cleared_acts = [
        a for a in activities
        if a["activity_type"] == "job_description_updated" and "cleared" in a["title"].lower()
    ]
    assert len(cleared_acts) >= 1


def test_update_job_description_404_unknown_submission(client):
    """Returns 404 when submission does not exist."""
    super_headers, _ = _create_super_admin(client)
    resp = client.patch(
        "/api/v1/admin/submissions/no-such-id/job-description",
        headers=super_headers,
        json={"job_description": JD_TEXT},
    )
    assert resp.status_code == 404


def test_update_job_description_403_unassigned_sub_admin(client):
    """Sub-admin cannot update JD for a submission not assigned to them."""
    super_headers, _ = _create_super_admin(client)
    sub_headers, _ = _create_sub_admin(client)
    submission_id = _create_submission(client)

    resp = client.patch(
        f"/api/v1/admin/submissions/{submission_id}/job-description",
        headers=sub_headers,
        json={"job_description": JD_TEXT},
    )
    assert resp.status_code == 403
    assert "not assigned" in resp.json()["detail"]["message"].lower()


def test_update_job_description_401_unauthenticated(client):
    """Unauthenticated request returns 401."""
    sub_id = _create_submission(client)
    resp = client.patch(
        f"/api/v1/admin/submissions/{sub_id}/job-description",
        json={"job_description": JD_TEXT},
    )
    assert resp.status_code == 401


def test_job_description_on_submission_creation(client):
    """job_description submitted via intake form is stored on the Submission record."""
    resp = client.post("/api/v1/public/submissions", json={
        "first_name": "Linda", "last_name": "Lee",
        "email": "linda.lee@example.com",
        "target_position": "DevOps Engineer",
        "job_description": "We need a DevOps engineer to manage our Kubernetes clusters.",
        "raw_data": {"education": [], "experience": [], "skills": [], "certifications": []},
    })
    assert resp.status_code == 200
    sub_id = resp.json()["data"]["submission_id"]

    super_headers, _ = _create_super_admin(client)
    get_resp = client.get(f"/api/v1/admin/submissions/{sub_id}", headers=super_headers)
    assert get_resp.status_code == 200
    assert "Kubernetes" in get_resp.json()["data"]["job_description"]
