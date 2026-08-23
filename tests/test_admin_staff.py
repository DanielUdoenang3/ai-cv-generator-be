def test_admin_staff_management_flow(client):
    # 1. Create and login Super Admin
    client.post("/api/v1/admin/auth/create-admin", json={
        "first_name": "Super",
        "last_name": "Boss",
        "email": "superboss@example.com",
        "password": "Password123!",
        "role": "super_admin"
    })
    login_super = client.post("/api/v1/admin/auth/login", json={
        "email": "superboss@example.com",
        "password": "Password123!"
    })
    super_headers = {"Authorization": f"Bearer {login_super.json()['data']['access_token']}"}
    super_id = login_super.json()["data"]["id"]

    # 2. Create staff member via Staff API (Post /staff)
    res_create = client.post(
        "/api/v1/admin/staff",
        headers=super_headers,
        json={
            "first_name": "Sarah",
            "last_name": "Johnson",
            "email": "sarahjohnson@example.com",
            "password": "Password123!",
            "role": "sub_admin",
            "phone": "+12345678",
            "gender": "female"
        }
    )
    assert res_create.status_code == 200
    assert res_create.json()["status_code"] == 201
    staff_id = res_create.json()["data"]["id"]

    # 3. Create a public submission and assign to Sarah
    res_sub = client.post("/api/v1/public/submissions", json={
        "first_name": "John",
        "last_name": "Client",
        "email": "john@client.com",
        "target_position": "Product Manager",
        "raw_data": {"education": [], "experience": [], "skills": []}
    })
    sub_id = res_sub.json()["data"]["submission_id"]

    # Assign submission to Sarah
    client.patch(
        f"/api/v1/admin/submissions/{sub_id}/assign",
        headers=super_headers,
        json={"assigned_to_id": staff_id}
    )

    # 4. Fetch staff list & check workload stats
    res_list = client.get("/api/v1/admin/staff", headers=super_headers)
    assert res_list.status_code == 200
    list_data = res_list.json()["data"]
    
    # We should have at least 2 admins (SuperBoss + Sarah)
    assert list_data["stats"]["total_staff"] >= 2
    assert list_data["stats"]["active_members"] >= 2
    
    # Find Sarah Johnson in the list
    sarah = next(s for s in list_data["staff"] if s["id"] == staff_id)
    assert sarah["active_count"] == 1  # Assigned PM task is active
    assert sarah["completed_count"] == 0

    # 5. Try self-deletion (should fail)
    res_self_del = client.delete(f"/api/v1/admin/staff/{super_id}", headers=super_headers)
    assert res_self_del.status_code == 400
    assert "cannot delete your own" in res_self_del.json()["detail"]["message"]

    # 6. Delete Sarah Johnson (should succeed and unassign task)
    res_del = client.delete(f"/api/v1/admin/staff/{staff_id}", headers=super_headers)
    assert res_del.status_code == 200

    # 7. Check that submission is now unassigned & audit activity is created
    res_sub_detail = client.get(f"/api/v1/admin/submissions/{sub_id}", headers=super_headers)
    sub_data = res_sub_detail.json()["data"]
    assert sub_data["assigned_to"] is None
    
    # Verify the activity timeline details contain the unassignment details
    activities = sub_data["activities"]
    unassign_act = next(
        a for a in activities 
        if a["activity_type"] == "assigned" and "account deletion" in a["description"]
    )
    assert unassign_act is not None
