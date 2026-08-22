import pytest
from app.models.enums import SubmissionStatus, AdminRole


def _create_admin(client, email, password, role, first_name="Test", last_name="User"):
    res = client.post("/api/v1/admin/auth/create-admin", json={
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "password": password,
        "role": role
    })
    assert res.status_code == 201 or res.status_code == 200
    
    # Login to get token
    login_res = client.post("/api/v1/admin/auth/login", json={
        "email": email,
        "password": password
    })
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    user_id = login_res.json()["data"]["id"]
    return {"Authorization": f"Bearer {token}"}, user_id


def _create_submission(client, first_name, last_name, email, target_position):
    res = client.post("/api/v1/public/submissions", json={
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "target_position": target_position,
        "raw_data": {"education": [], "experience": [], "skills": [], "certifications": []}
    })
    assert res.status_code == 201 or res.status_code == 200
    data = res.json()["data"]
    return data["submission_id"], data["access_token"]


def test_dashboard_stats_and_recent_submissions(client):
    # 1. Create Super Admin & Sub Admin
    super_headers, super_id = _create_admin(client, "super@example.com", "Pass1234!", "super_admin", "Super", "Admin")
    sub_headers, sub_id = _create_admin(client, "sub@example.com", "Pass1234!", "sub_admin", "Sub", "Admin")

    # 2. Create 3 client submissions
    sub1_id, sub1_token = _create_submission(client, "Alice", "Smith", "alice@example.com", "Python Dev")
    sub2_id, sub2_token = _create_submission(client, "Bob", "Jones", "bob@example.com", "React Dev")
    sub3_id, sub3_token = _create_submission(client, "Charlie", "Brown", "charlie@example.com", "DevOps Eng")

    # By default, all 3 are "new" and unassigned.
    # 3. Super Admin assigns Sub2 and Sub3 to Sub Admin
    res = client.patch(f"/api/v1/admin/submissions/{sub2_id}/assign", headers=super_headers, json={"assigned_to_id": sub_id})
    assert res.status_code == 200
    res = client.patch(f"/api/v1/admin/submissions/{sub3_id}/assign", headers=super_headers, json={"assigned_to_id": sub_id})
    assert res.status_code == 200

    # 4. Super Admin updates status: Sub2 -> in_progress, Sub3 -> completed
    res = client.patch(f"/api/v1/admin/submissions/{sub2_id}/status", headers=super_headers, json={"status": "in_progress"})
    assert res.status_code == 200
    res = client.patch(f"/api/v1/admin/submissions/{sub3_id}/status", headers=super_headers, json={"status": "completed"})
    assert res.status_code == 200

    # 5. Client sends a message to Sub2 (to make its chat active)
    sub2_access_token = sub2_token
    
    # Client sends a message
    res = client.post(
        f"/api/v1/public/submissions/{sub2_id}/messages",
        headers={"X-Client-Access-Token": sub2_access_token},
        data={"message": "Hi, any updates on my CV?"}
    )
    assert res.status_code == 200
    assert res.json()["status_code"] == 201

    # ------------------- TEST STATS -------------------
    
    # Super Admin stats: 1 new, 1 in_progress, 1 completed, 1 active chat (Sub2)
    stats_res = client.get("/api/v1/admin/dashboard/stats", headers=super_headers)
    assert stats_res.status_code == 200
    stats_data = stats_res.json()["data"]
    assert stats_data["new_requests"] == 1
    assert stats_data["in_progress"] == 1
    assert stats_data["completed"] == 1
    assert stats_data["active_chats"] == 1

    # Sub Admin stats: 0 new (since they are unassigned), 1 in_progress, 1 completed, 1 active chat
    sub_stats_res = client.get("/api/v1/admin/dashboard/stats", headers=sub_headers)
    assert sub_stats_res.status_code == 200
    sub_stats_data = sub_stats_res.json()["data"]
    assert sub_stats_data["new_requests"] == 0
    assert sub_stats_data["in_progress"] == 1
    assert sub_stats_data["completed"] == 1
    assert sub_stats_data["active_chats"] == 1

    # ------------------- TEST RECENT SUBMISSIONS -------------------

    # Super Admin recent submissions: should see all 3 submissions
    recent_res = client.get("/api/v1/admin/dashboard/recent-submissions", headers=super_headers)
    assert recent_res.status_code == 200
    recent_data = recent_res.json()["data"]
    assert recent_data["total"] == 3
    assert len(recent_data["submissions"]) == 3

    # Sorting verification (asc vs desc by target_position)
    # DevOps Eng, Python Dev, React Dev
    recent_asc = client.get(
        "/api/v1/admin/dashboard/recent-submissions?sort_by=target_position&sort_order=asc",
        headers=super_headers
    )
    assert recent_asc.status_code == 200
    submissions_asc = recent_asc.json()["data"]["submissions"]
    assert submissions_asc[0]["target_position"] == "DevOps Eng"
    assert submissions_asc[1]["target_position"] == "Python Dev"
    assert submissions_asc[2]["target_position"] == "React Dev"

    # Search verification
    search_res = client.get("/api/v1/admin/dashboard/recent-submissions?search=Alice", headers=super_headers)
    assert search_res.status_code == 200
    search_data = search_res.json()["data"]
    assert search_data["total"] == 1
    assert search_data["submissions"][0]["client"]["first_name"] == "Alice"

    # Status filter verification
    status_res = client.get("/api/v1/admin/dashboard/recent-submissions?status=completed", headers=super_headers)
    assert status_res.status_code == 200
    status_data = status_res.json()["data"]
    assert status_data["total"] == 1
    assert status_data["submissions"][0]["status"] == "completed"

    # Assigned To Filter verification
    assign_res = client.get(f"/api/v1/admin/dashboard/recent-submissions?assigned_to_id={sub_id}", headers=super_headers)
    assert assign_res.status_code == 200
    assign_data = assign_res.json()["data"]
    assert assign_data["total"] == 2  # Sub2 and Sub3

    unassign_res = client.get("/api/v1/admin/dashboard/recent-submissions?assigned_to_id=unassigned", headers=super_headers)
    assert unassign_res.status_code == 200
    unassign_data = unassign_res.json()["data"]
    assert unassign_data["total"] == 1  # Sub1

    # Pagination verification
    pag_res = client.get("/api/v1/admin/dashboard/recent-submissions?page=1&limit=2", headers=super_headers)
    assert pag_res.status_code == 200
    pag_data = pag_res.json()["data"]
    assert pag_data["total"] == 3
    assert pag_data["limit"] == 2
    assert pag_data["pages"] == 2
    assert len(pag_data["submissions"]) == 2

    # Sub Admin RBAC verification: should only see Sub2 and Sub3 (total 2)
    sub_recent_res = client.get("/api/v1/admin/dashboard/recent-submissions", headers=sub_headers)
    assert sub_recent_res.status_code == 200
    sub_recent_data = sub_recent_res.json()["data"]
    assert sub_recent_data["total"] == 2
    assert all(s["assigned_to"]["id"] == sub_id for s in sub_recent_data["submissions"])

    # Unauthenticated user check
    unauth_res = client.get("/api/v1/admin/dashboard/stats")
    assert unauth_res.status_code == 401
