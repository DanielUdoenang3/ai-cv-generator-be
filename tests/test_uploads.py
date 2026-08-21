from unittest.mock import patch

def test_single_file_upload(client, mock_cloudinary):
    fake_pdf = ("resume.pdf", b"fake pdf content", "application/pdf")
    response = client.post("/api/v1/public/upload", files={"files": fake_pdf})
    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 201
    assert data["status"] == "success"
    assert "url" in data["data"]
    assert data["data"]["url"] == "https://res.cloudinary.com/demo/image/upload/v1600000000/ai_cv_generator/test.pdf"


def test_multi_file_upload(client, mock_cloudinary):
    file1 = ("cert1.pdf", b"pdf1", "application/pdf")
    file2 = ("cert2.pdf", b"pdf2", "application/pdf")
    response = client.post(
        "/api/v1/public/upload",
        files=[("files", file1), ("files", file2)]
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 201
    assert data["data"]["total"] == 2
    assert len(data["data"]["files"]) == 2


def test_invalid_file_extension_rejected(client):
    bad_file = ("script.exe", b"malicious binary", "application/x-msdownload")
    response = client.post("/api/v1/public/upload", files={"files": bad_file})
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Unsupported file extension" in data["detail"]["message"]
