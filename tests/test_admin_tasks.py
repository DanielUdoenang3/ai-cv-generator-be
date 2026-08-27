from datetime import datetime, timedelta, timezone

def test_admin_task_management_full_flow(client):
    # 1. Create and login Admin
    client.post(
        "/api/v1/admin/auth/create-admin",
        json={
            "first_name": "Task",
            "last_name": "Master",
            "email": "taskmaster@example.com",
            "password": "Password123!",
            "role": "super_admin",
        },
    )
    login_res = client.post(
        "/api/v1/admin/auth/login",
        json={"email": "taskmaster@example.com", "password": "Password123!"},
    )
    headers = {"Authorization": f"Bearer {login_res.json()['data']['access_token']}"}
    admin_id = login_res.json()["data"]["id"]

    # 2. Create public submission
    res_sub = client.post(
        "/api/v1/public/submissions",
        json={
            "first_name": "Robert",
            "last_name": "Kim",
            "email": "robert.kim@example.com",
            "target_position": "Backend Lead",
            "raw_data": {"education": [], "experience": [], "skills": []},
        },
    )
    sub_id = res_sub.json()["data"]["submission_id"]

    # 3. Create tasks
    # Task 1: Normal priority, todo, overdue (deadline yesterday)
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    res_t1 = client.post(
        "/api/v1/admin/tasks",
        headers=headers,
        json={
            "title": "Proofread and format",
            "description": "Check grammar, spelling, and overall formatting",
            "submission_id": sub_id,
            "assigned_to_id": admin_id,
            "priority": "normal",
            "status": "todo",
            "deadline": yesterday,
        },
    )
    assert res_t1.status_code == 200
    assert res_t1.json()["status_code"] == 201
    task1_id = res_t1.json()["data"]["id"]
    assert res_t1.json()["data"]["submission"]["client_name"] == "Robert Kim"

    # Task 2: High priority, in_progress
    res_t2 = client.post(
        "/api/v1/admin/tasks",
        headers=headers,
        json={
            "title": "Review work experience section",
            "description": "Client needs help restructuring leadership roles",
            "submission_id": sub_id,
            "assigned_to_id": admin_id,
            "priority": "high",
            "status": "in_progress",
        },
    )
    assert res_t2.status_code == 200
    task2_id = res_t2.json()["data"]["id"]

    # 4. Fetch task metrics & list
    res_list = client.get("/api/v1/admin/tasks", headers=headers)
    assert res_list.status_code == 200
    data = res_list.json()["data"]
    stats = data["stats"]
    assert stats["total_tasks"] >= 2
    assert stats["my_tasks"] >= 2
    assert stats["overdue"] >= 1
    assert stats["high_priority"] >= 1
    assert stats["todo_count"] >= 1
    assert stats["in_progress_count"] >= 1

    # 5. Filter tests
    # Filter view_tab=overdue
    res_overdue = client.get("/api/v1/admin/tasks?view_tab=overdue", headers=headers)
    assert res_overdue.status_code == 200
    overdue_ids = [t["id"] for t in res_overdue.json()["data"]["tasks"]]
    assert task1_id in overdue_ids

    # Filter view_tab=high_priority
    res_high = client.get("/api/v1/admin/tasks?view_tab=high_priority", headers=headers)
    assert res_high.status_code == 200
    high_ids = [t["id"] for t in res_high.json()["data"]["tasks"]]
    assert task2_id in high_ids

    # Filter search by title
    res_search = client.get("/api/v1/admin/tasks?search=Proofread", headers=headers)
    assert res_search.status_code == 200
    assert len(res_search.json()["data"]["tasks"]) == 1
    assert res_search.json()["data"]["tasks"][0]["id"] == task1_id

    # 6. Fetch single task details
    res_detail = client.get(f"/api/v1/admin/tasks/{task1_id}", headers=headers)
    assert res_detail.status_code == 200
    assert res_detail.json()["data"]["title"] == "Proofread and format"

    # 7. Update task (move column to 'done' and change priority to 'high')
    res_update = client.patch(
        f"/api/v1/admin/tasks/{task1_id}",
        headers=headers,
        json={"status": "done", "priority": "high"},
    )
    assert res_update.status_code == 200
    assert res_update.json()["data"]["status"] == "done"
    assert res_update.json()["data"]["priority"] == "high"

    # 8. Delete task
    res_del = client.delete(f"/api/v1/admin/tasks/{task1_id}", headers=headers)
    assert res_del.status_code == 200
    assert res_del.json()["message"] == "Task deleted successfully"

    # Verify task is deleted
    res_get_deleted = client.get(f"/api/v1/admin/tasks/{task1_id}", headers=headers)
    assert res_get_deleted.status_code == 404
