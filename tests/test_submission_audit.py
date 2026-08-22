import pytest
from datetime import datetime, timezone
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
    data = login_res.json()["data"]
    return {"Authorization": f"Bearer {data['access_token']}"}, data["id"]


def _create_submission(client, first_name, last_name, email, target_position, target_company=None, priority=None):
    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "target_position": target_position,
        "raw_data": {"education": [], "experience": [], "skills": [], "certifications": []}
    }
    if target_company:
        payload["target_company"] = target_company
    if priority:
        payload["priority"] = priority

    res = client.post("/api/v1/public/submissions", json=payload)
    assert res.status_code == 201 or res.status_code == 200
    data = res.json()["data"]
    return data["submission_id"], data["access_token"]


def test_submission_reference_id_and_activity_audit(client):
    # 1. Create Admins
    super_headers, super_id = _create_admin(client, "super@example.com", "Pass1234!", "super_admin", "Super", "Admin")
    sub_headers, sub_id = _create_admin(client, "sub@example.com", "Pass1234!", "sub_admin", "Sarah", "Johnson")

    # 2. Create first submission
    current_year = datetime.now(timezone.utc).year
    expected_ref_1 = f"SUB-{current_year}-001"
    expected_ref_2 = f"SUB-{current_year}-002"

    sub1_id, token1 = _create_submission(
        client, "Amanda", "Foster", "amanda@email.com", "HR Manager", target_company="LinkedIn", priority="low"
    )

    # 3. Retrieve submission details and check fields & initial activity log
    res = client.get(f"/api/v1/admin/submissions/{sub1_id}", headers=super_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["reference_id"] == expected_ref_1
    assert data["target_company"] == "LinkedIn"
    assert data["priority"] == "low"
    assert data["status"] == "new"
    
    # Check activity timeline has 1 event: Submission Created
    activities = data["activities"]
    assert len(activities) == 1
    assert activities[0]["activity_type"] == "submission_created"
    assert activities[0]["title"] == "Submission Created"
    assert activities[0]["description"] == "Client submitted CV request through the form"

    # 4. Create second submission to verify sequential reference ID increment
    sub2_id, token2 = _create_submission(
        client, "Bob", "Smith", "bob.smith@email.com", "Software Engineer"
    )
    res2 = client.get(f"/api/v1/admin/submissions/{sub2_id}", headers=super_headers)
    assert res2.status_code == 200
    data2 = res2.json()["data"]
    assert data2["reference_id"] == expected_ref_2
    assert data2["priority"] == "normal"  # default value

    # 5. Assign sub1 to Sarah Johnson (Sub Admin)
    # This should log two activities: assignment and status escalation to "in_progress"
    assign_res = client.patch(
        f"/api/v1/admin/submissions/{sub1_id}/assign",
        headers=super_headers,
        json={"assigned_to_id": sub_id}
    )
    assert assign_res.status_code == 200

    res_updated = client.get(f"/api/v1/admin/submissions/{sub1_id}", headers=super_headers)
    assert res_updated.status_code == 200
    data_updated = res_updated.json()["data"]
    assert data_updated["status"] == "in_progress"

    # Verify activity timeline has 3 items in reverse chronological order (newest first):
    # 1. Status Changed to In Progress (since auto-escalated after assignment)
    # 2. Assigned to Sarah Johnson
    # 3. Submission Created
    acts = data_updated["activities"]
    assert len(acts) == 3
    
    assert acts[0]["activity_type"] == "status_changed"
    assert acts[0]["title"] == "Status Changed to In Progress"
    assert acts[0]["description"] == "Work started on CV generation and optimization"
    assert acts[0]["actor_id"] == super_id
    assert acts[0]["actor_name"] == "Super Admin"

    assert acts[1]["activity_type"] == "assigned"
    assert acts[1]["title"] == "Assigned to Sarah Johnson"
    assert acts[1]["description"] == "Submission assigned for review and processing"
    assert acts[1]["actor_id"] == super_id
    assert acts[1]["actor_name"] == "Super Admin"

    assert acts[2]["activity_type"] == "submission_created"
    assert acts[2]["actor_name"] is None

    # 6. Update Status to "review"
    # This verifies the new status choice and the status changed activity logger
    status_res = client.patch(
        f"/api/v1/admin/submissions/{sub1_id}/status",
        headers=super_headers,
        json={"status": "review"}
    )
    assert status_res.status_code == 200

    res_review = client.get(f"/api/v1/admin/submissions/{sub1_id}", headers=super_headers)
    assert res_review.status_code == 200
    data_review = res_review.json()["data"]
    assert data_review["status"] == "review"

    # Verify activity timeline has 4 items now, with newest first
    acts_review = data_review["activities"]
    assert len(acts_review) == 4
    assert acts_review[0]["activity_type"] == "status_changed"
    assert acts_review[0]["title"] == "Status Changed to Review"
    assert acts_review[0]["description"] == "Submission moved to review stage"
    assert acts_review[0]["actor_id"] == super_id
    assert acts_review[0]["actor_name"] == "Super Admin"
