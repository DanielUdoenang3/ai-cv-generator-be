def _create_test_submission(client):
    payload = {
        "first_name": "Sarah",
        "last_name": "Connor",
        "email": "sarah.connor@example.com",
        "target_position": "Security Consultant",
        "raw_data": {"education": [], "experience": [], "skills": [], "certifications": []}
    }
    res = client.post("/api/v1/public/submissions", json=payload)
    data = res.json()["data"]
    return data["submission_id"], data["access_token"]


def test_get_messages_empty_initially(client):
    sub_id, access_token = _create_test_submission(client)
    headers = {"X-Client-Access-Token": access_token}

    res = client.get(f"/api/v1/public/submissions/{sub_id}/messages", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status_code"] == 200
    assert len(data["data"]["messages"]) == 0


def test_client_send_text_message(client):
    sub_id, access_token = _create_test_submission(client)
    headers = {"X-Client-Access-Token": access_token}

    res = client.post(
        f"/api/v1/public/submissions/{sub_id}/messages",
        headers=headers,
        data={"message": "Hello! I have updated my work history."}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status_code"] == 201
    assert data["data"]["message"] == "Hello! I have updated my work history."
    assert data["data"]["sender_type"] == "client"


def test_client_send_message_with_attachments(client, mock_cloudinary):
    sub_id, access_token = _create_test_submission(client)
    headers = {"X-Client-Access-Token": access_token}

    fake_file = ("certificate.pdf", b"fake binary content", "application/pdf")

    res = client.post(
        f"/api/v1/public/submissions/{sub_id}/messages",
        headers=headers,
        data={"message": "Attached is my latest certificate."},
        files={"files": fake_file}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status_code"] == 201
    assert len(data["data"]["attachments"]) == 1
    assert data["data"]["attachments"][0]["url"] == "https://res.cloudinary.com/demo/image/upload/v1600000000/ai_cv_generator/test.pdf"


def test_client_chat_unauthorized(client):
    headers = {"X-Client-Access-Token": "invalid-secret-token"}
    res = client.get("/api/v1/public/submissions/fake-sub-id/messages", headers=headers)
    assert res.status_code == 404
    assert res.json()["detail"]["message"] == "Submission not found or access token is invalid"
