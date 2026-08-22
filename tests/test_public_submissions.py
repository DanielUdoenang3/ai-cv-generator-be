def test_create_submission_success(client):
    payload = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "+1234567890",
        "target_position": "Full Stack Engineer",
        "job_description": "Seeking Python and React developer",
        "raw_data": {
            "education": [
                {
                    "institution": "MIT",
                    "degree": "B.Sc Computer Science",
                    "start_date": "2018-09-01",
                    "end_date": "2022-06-01"
                }
            ],
            "experience": [],
            "skills": ["Python", "FastAPI", "React"],
            "certifications": []
        }
    }

    response = client.post("/api/v1/public/submissions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 201
    assert "submission_id" in data["data"]
    assert "access_token" in data["data"]
    assert data["data"]["client"]["email"] == "john.doe@example.com"


def test_create_submission_with_uploaded_cv(client):
    payload = {
        "first_name": "Alice",
        "last_name": "Smith",
        "email": "alice.smith@example.com",
        "target_position": "Data Scientist",
        "existing_cv_url": "https://res.cloudinary.com/demo/image/upload/v1/resumes/alice.pdf",
        "raw_data": {
            "education": [],
            "experience": [],
            "skills": ["Python", "Pandas"],
            "certifications": []
        }
    }

    response = client.post("/api/v1/public/submissions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 201
    assert "submission_id" in data["data"]


def test_create_submission_validation_errors(client):
    invalid_payload = {
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "target_position": "Engineer",
        "raw_data": {"education": [], "experience": [], "skills": [], "certifications": []}
    }
    response = client.post("/api/v1/public/submissions", json=invalid_payload)
    assert response.status_code == 422


def test_create_submission_invalid_email(client):
    invalid_payload = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "not-an-email",
        "target_position": "Engineer",
        "raw_data": {"education": [], "experience": [], "skills": [], "certifications": []}
    }
    response = client.post("/api/v1/public/submissions", json=invalid_payload)
    assert response.status_code == 422


def test_get_client_submission_status(client):
    payload = {
        "first_name": "Mark",
        "last_name": "Taylor",
        "email": "mark.taylor@example.com",
        "target_position": "DevOps Engineer",
        "raw_data": {"education": [], "experience": [], "skills": [], "certifications": []}
    }
    create_res = client.post("/api/v1/public/submissions", json=payload)
    sub_id = create_res.json()["data"]["submission_id"]
    access_token = create_res.json()["data"]["access_token"]

    headers = {"X-Client-Access-Token": access_token}
    res = client.get(f"/api/v1/public/submissions/{sub_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["status_code"] == 200
    assert res.json()["data"]["submission_id"] == sub_id


def test_get_client_submission_invalid_token(client):
    headers = {"X-Client-Access-Token": "invalid-token-123"}
    res = client.get("/api/v1/public/submissions/non-existent-id", headers=headers)
    assert res.status_code == 404
    assert res.json()["detail"]["message"] == "Submission not found or access token is invalid"
