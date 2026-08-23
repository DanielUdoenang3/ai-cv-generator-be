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


def test_client_edit_message(client):
    sub_id, access_token = _create_test_submission(client)
    headers = {"X-Client-Access-Token": access_token}

    # 1. Send message
    res = client.post(
        f"/api/v1/public/submissions/{sub_id}/messages",
        headers=headers,
        data={"message": "Original Message"}
    )
    msg_id = res.json()["data"]["id"]

    # 2. Edit message
    res_edit = client.patch(
        f"/api/v1/public/submissions/{sub_id}/messages/{msg_id}",
        headers=headers,
        json={"message": "Updated Message"}
    )
    assert res_edit.status_code == 200
    assert res_edit.json()["data"]["message"] == "Updated Message"

    # 3. Retrieve messages and verify edit
    res_get = client.get(f"/api/v1/public/submissions/{sub_id}/messages", headers=headers)
    messages = res_get.json()["data"]["messages"]
    assert len(messages) == 1
    assert messages[0]["message"] == "Updated Message"


def test_client_delete_message(client):
    sub_id, access_token = _create_test_submission(client)
    headers = {"X-Client-Access-Token": access_token}

    # 1. Send message
    res = client.post(
        f"/api/v1/public/submissions/{sub_id}/messages",
        headers=headers,
        data={"message": "Delete Me"}
    )
    msg_id = res.json()["data"]["id"]

    # 2. Delete message
    res_delete = client.delete(
        f"/api/v1/public/submissions/{sub_id}/messages/{msg_id}",
        headers=headers
    )
    assert res_delete.status_code == 200

    # 3. Retrieve messages and verify deletion
    res_get = client.get(f"/api/v1/public/submissions/{sub_id}/messages", headers=headers)
    assert len(res_get.json()["data"]["messages"]) == 0


def test_client_mark_messages_read(client):
    sub_id, access_token = _create_test_submission(client)
    headers = {"X-Client-Access-Token": access_token}

    # Mark messages as read (checks that DB update/broadcast logic runs without error)
    res = client.patch(
        f"/api/v1/public/submissions/{sub_id}/messages/read",
        headers=headers
    )
    assert res.status_code == 200
    assert res.json()["data"]["read_by"] == "client"


def test_client_websocket_flow(client):
    sub_id, access_token = _create_test_submission(client)

    # 1. Connect websocket
    with client.websocket_connect(
        f"/api/v1/public/submissions/{sub_id}/ws?token={access_token}"
    ) as websocket:
        # 2. Test ping-pong
        websocket.send_json({"type": "ping"})
        data = websocket.receive_json()
        assert data["type"] == "pong"

        # 3. Test typing indicator
        websocket.send_json({"type": "typing", "is_typing": True})
        data = websocket.receive_json()
        assert data["event"] == "typing"
        assert data["data"]["sender_type"] == "client"
        assert data["data"]["is_typing"] is True


def test_client_websocket_auth_failure(client):
    sub_id, _ = _create_test_submission(client)
    from starlette.websockets import WebSocketDisconnect
    import pytest

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            f"/api/v1/public/submissions/{sub_id}/ws?token=invalid_token"
        ):
            pass
    assert exc_info.value.code == 4001

