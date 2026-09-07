"""
Tests for POST /api/v1/admin/submissions/{submission_id}/tailor

Covers:
- Happy path: assigned admin tailors resume — returns 4 documents (PDF+DOCX resume+cover letter)
- Happy path: super admin can tailor any submission
- Returns correct document kinds (resume + cover_letter) and file types (pdf + docx)
- Version increments on repeated tailoring
- 400 when no resume content is saved on the submission
- 404 on non-existent submission
- 403 for sub-admin on unassigned submission
- 401 for unauthenticated requests
- LLM failure → 500/503 propagated cleanly
- Submission status changes to 'review' after successful tailor
- AiGeneration record is created with correct fields
- Activity log entry is created
"""

import json
from unittest.mock import AsyncMock, patch


# ── Mock data ─────────────────────────────────────────────────────────────────

MOCK_CV_JSON = {
    "personal_info": {
        "full_name": "Jane Render",
        "email": "jane.render@example.com",
        "phone": "+1 555 000 0000",
        "location": "New York, NY",
        "linkedin": None,
        "portfolio": None,
        "target_role": "Senior Software Engineer",
    },
    "professional_summary": (
        "Seasoned software engineer with 8+ years building scalable Python APIs. "
        "Reduced latency 40% at Acme Corp."
    ),
    "work_experience": [
        {
            "job_title": "Senior Software Engineer",
            "company": "Acme Corp",
            "location": "New York, NY",
            "start_date": "Jan 2020",
            "end_date": None,
            "is_current": True,
            "bullet_points": [
                "Reduced API latency 40% via Redis caching.",
                "Led migration of monolith to microservices.",
            ],
        }
    ],
    "skills": {"Backend": ["Python", "FastAPI", "PostgreSQL"]},
    "technical_tools": "Python, FastAPI, PostgreSQL, Redis, Docker",
    "education": [
        {
            "degree": "B.S. Computer Science",
            "institution": "MIT",
            "location": "Cambridge, MA",
            "start_date": "Sep 2012",
            "graduation_year": "May 2016",
            "honors": None,
        }
    ],
    "projects": [],
    "certifications": [],
}

MOCK_COVER_LETTER_JSON = {
    "date": "September 7, 2026",
    "salutation": "Dear Hiring Manager,",
    "body_paragraphs": [
        "I am excited to apply for the Senior Software Engineer role.",
        "My 8+ years of Python expertise make me an ideal candidate.",
        "I look forward to contributing to your engineering team.",
    ],
    "sign_off": "Warm regards,",
    "signatory_name": "Jane Render",
}

MOCK_LLM_RESULT = {
    **MOCK_CV_JSON,
    "cover_letter": MOCK_COVER_LETTER_JSON,
}

MOCK_CLOUDINARY_RESP = {
    "secure_url": "https://res.cloudinary.com/demo/raw/upload/v1/ai_cv_generator/documents/test.pdf",
    "public_id": "ai_cv_generator/documents/test_pdf_v1",
}

MOCK_PDF_BYTES = b"%PDF-1.4 mock pdf bytes"
MOCK_DOCX_BYTES = b"PK mock docx bytes"


# ── helpers ───────────────────────────────────────────────────────────────────

def _create_super_admin(client, email="tailor.super@example.com"):
    client.post("/api/v1/admin/auth/create-admin", json={
        "first_name": "Super", "last_name": "Admin",
        "email": email, "password": "Password123!", "role": "super_admin",
    })
    resp = client.post("/api/v1/admin/auth/login",
                       json={"email": email, "password": "Password123!"})
    data = resp.json()["data"]
    return {"Authorization": f"Bearer {data['access_token']}"}, data["id"]


def _create_sub_admin(client, email="tailor.sub@example.com"):
    client.post("/api/v1/admin/auth/create-admin", json={
        "first_name": "Sub", "last_name": "Admin",
        "email": email, "password": "Password123!", "role": "sub_admin",
    })
    resp = client.post("/api/v1/admin/auth/login",
                       json={"email": email, "password": "Password123!"})
    data = resp.json()["data"]
    return {"Authorization": f"Bearer {data['access_token']}"}, data["id"]


def _create_submission(client, email="tailor.client@example.com"):
    resp = client.post("/api/v1/public/submissions", json={
        "first_name": "Jane", "last_name": "Render",
        "email": email,
        "target_position": "Senior Software Engineer",
        "target_company": "Acme Corp",
        "job_description": "Looking for a senior engineer with Python and API experience.",
        "raw_data": {"education": [], "experience": [], "skills": ["Python", "FastAPI"]},
    })
    return resp.json()["data"]["submission_id"]


def _save_resume(client, headers, sub_id):
    """Pre-condition: save resume text so tailor endpoint doesn't 400."""
    client.patch(
        f"/api/v1/admin/submissions/{sub_id}/resume-text",
        headers=headers,
        json={
            "saved_resume_text": (
                "Jane Render | Senior Software Engineer\n"
                "8+ years Python expertise. Reduced API latency by 40% at Acme Corp.\n"
                "Education: B.S. Computer Science, MIT, 2016."
            )
        },
    )


def _mock_tailor(fn):
    """Decorator to patch the LLM call and rendering stack for tailor endpoint."""
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        llm_return = {
            "structured_cv": dict(MOCK_LLM_RESULT),  # includes cover_letter key
            "input_tokens": 1500,
            "output_tokens": 800,
            "cost": 0.012,
            "model_used": "gpt-4o",
            "provider_used": "openai",
            "is_mock": False,
        }
        with patch(
            "app.services.ai_service.call_llm_provider",
            new_callable=AsyncMock,
            return_value=llm_return,
        ), patch(
            "app.services.document_service.render_pdf_bytes",
            return_value=MOCK_PDF_BYTES,
        ), patch(
            "app.services.document_service.render_docx_bytes",
            return_value=MOCK_DOCX_BYTES,
        ), patch(
            "app.services.document_service.render_cover_letter_docx_bytes",
            return_value=MOCK_DOCX_BYTES,
        ), patch(
            "app.services.document_service.upload_to_cloudinary",
            return_value=MOCK_CLOUDINARY_RESP,
        ):
            return fn(*args, **kwargs)

    return wrapper


# ── Tests ─────────────────────────────────────────────────────────────────────

@_mock_tailor
def test_tailor_resume_success_returns_four_documents(client):
    """Happy path: tailor returns 4 documents (resume PDF, resume DOCX, CL PDF, CL DOCX)."""
    super_headers, _ = _create_super_admin(client)
    sub_id = _create_submission(client)
    _save_resume(client, super_headers, sub_id)

    resp = client.post(
        f"/api/v1/admin/submissions/{sub_id}/tailor",
        headers=super_headers,
        json={"provider": "openai", "model": "gpt-4o"},
    )
    # success_response() always returns HTTP 200; the inner status_code carries 201
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["status_code"] == 201
    assert "tailored successfully" in data["message"].lower()

    docs = data["data"]["documents"]
    assert len(docs) == 4

    kinds = [d["document_kind"] for d in docs]
    assert kinds.count("resume") == 2
    assert kinds.count("cover_letter") == 2

    file_types = [d["file_type"] for d in docs]
    assert "pdf" in file_types
    assert "docx" in file_types


@_mock_tailor
def test_tailor_resume_response_shape(client):
    """Response body has all expected top-level keys."""
    super_headers, _ = _create_super_admin(client)
    sub_id = _create_submission(client)
    _save_resume(client, super_headers, sub_id)

    resp = client.post(
        f"/api/v1/admin/submissions/{sub_id}/tailor",
        headers=super_headers,
        json={"provider": "openai", "model": "gpt-4o"},
    )
    # HTTP 200 always for success_response; inner status_code carries 201
    assert resp.status_code == 200
    assert resp.json()["status_code"] == 201
    d = resp.json()["data"]
    assert "ai_generation_id" in d
    assert "submission_id" in d
    assert d["submission_id"] == sub_id
    assert "model" in d
    assert "provider_used" in d
    assert "input_tokens" in d
    assert "output_tokens" in d
    assert "cost" in d
    assert isinstance(d["documents"], list)


@_mock_tailor
def test_tailor_resume_changes_submission_status_to_review(client):
    """After tailoring, submission status is updated to 'review'."""
    super_headers, _ = _create_super_admin(client)
    sub_id = _create_submission(client)
    _save_resume(client, super_headers, sub_id)

    # Initial status should be 'new'
    pre = client.get(f"/api/v1/admin/submissions/{sub_id}", headers=super_headers)
    assert pre.json()["data"]["status"] == "new"

    client.post(
        f"/api/v1/admin/submissions/{sub_id}/tailor",
        headers=super_headers,
        json={"provider": "openai"},
    )

    post = client.get(f"/api/v1/admin/submissions/{sub_id}", headers=super_headers)
    assert post.json()["data"]["status"] == "review"


@_mock_tailor
def test_tailor_resume_creates_ai_generation_record(client):
    """A successful tailor creates an AiGeneration log entry."""
    super_headers, _ = _create_super_admin(client)
    sub_id = _create_submission(client)
    _save_resume(client, super_headers, sub_id)

    tailor_resp = client.post(
        f"/api/v1/admin/submissions/{sub_id}/tailor",
        headers=super_headers,
        json={"provider": "openai"},
    )
    ai_gen_id = tailor_resp.json()["data"]["ai_generation_id"]

    # Verify via generation history endpoint
    log_resp = client.get(
        f"/api/v1/admin/submissions/{sub_id}/generations",
        headers=super_headers,
    )
    assert log_resp.status_code == 200
    logs = log_resp.json()["data"]
    assert len(logs) >= 1
    gen = next((g for g in logs if g["id"] == ai_gen_id), None)
    assert gen is not None
    assert gen["status"] == "success"


@_mock_tailor
def test_tailor_resume_creates_activity_log(client):
    """Tailoring creates a 'status_changed' activity with 'Resume Tailored' title."""
    super_headers, _ = _create_super_admin(client)
    sub_id = _create_submission(client)
    _save_resume(client, super_headers, sub_id)

    client.post(
        f"/api/v1/admin/submissions/{sub_id}/tailor",
        headers=super_headers,
        json={"provider": "openai"},
    )

    get_resp = client.get(f"/api/v1/admin/submissions/{sub_id}", headers=super_headers)
    activities = get_resp.json()["data"]["activities"]
    tailor_act = next(
        (a for a in activities if a["title"] == "Resume Tailored"), None
    )
    assert tailor_act is not None
    assert tailor_act["activity_type"] == "status_changed"


@_mock_tailor
def test_tailor_resume_document_versions_increment(client):
    """Re-tailoring increments document version numbers."""
    super_headers, _ = _create_super_admin(client)
    sub_id = _create_submission(client)
    _save_resume(client, super_headers, sub_id)

    # First tailor — expect version 1
    resp1 = client.post(
        f"/api/v1/admin/submissions/{sub_id}/tailor",
        headers=super_headers,
        json={"provider": "openai"},
    )
    docs1 = resp1.json()["data"]["documents"]
    versions1 = [d["version"] for d in docs1]
    assert all(v == 1 for v in versions1)

    # Second tailor — expect version 2
    resp2 = client.post(
        f"/api/v1/admin/submissions/{sub_id}/tailor",
        headers=super_headers,
        json={"provider": "openai"},
    )
    docs2 = resp2.json()["data"]["documents"]
    versions2 = [d["version"] for d in docs2]
    assert all(v == 2 for v in versions2)


@_mock_tailor
def test_assigned_sub_admin_can_tailor(client):
    """An assigned sub-admin can call the tailor endpoint successfully."""
    super_headers, _ = _create_super_admin(client)
    sub_headers, sub_admin_id = _create_sub_admin(client)
    sub_id = _create_submission(client)
    _save_resume(client, super_headers, sub_id)

    # Assign
    client.patch(
        f"/api/v1/admin/submissions/{sub_id}/assign",
        headers=super_headers,
        json={"assigned_to_id": sub_admin_id},
    )

    resp = client.post(
        f"/api/v1/admin/submissions/{sub_id}/tailor",
        headers=sub_headers,
        json={"provider": "openai"},
    )
    assert resp.status_code == 200
    assert resp.json()["status_code"] == 201
    assert len(resp.json()["data"]["documents"]) == 4


def test_tailor_resume_400_no_resume_content(client):
    """Returns 400 when submission has no saved_resume_text and no raw_data."""
    super_headers, _ = _create_super_admin(client)

    # Create a submission with NO raw_data and NO saved_resume_text
    resp = client.post("/api/v1/public/submissions", json={
        "first_name": "Empty", "last_name": "Resume",
        "email": "empty.resume@example.com",
        "target_position": "Engineer",
    })
    sub_id = resp.json()["data"]["submission_id"]

    tailor_resp = client.post(
        f"/api/v1/admin/submissions/{sub_id}/tailor",
        headers=super_headers,
        json={"provider": "openai"},
    )
    assert tailor_resp.status_code == 400
    assert "resume" in tailor_resp.json()["detail"]["message"].lower()


def test_tailor_resume_404_unknown_submission(client):
    """Returns 404 for a non-existent submission."""
    super_headers, _ = _create_super_admin(client)
    resp = client.post(
        "/api/v1/admin/submissions/nonexistent-id/tailor",
        headers=super_headers,
        json={"provider": "openai"},
    )
    assert resp.status_code == 404


def test_tailor_resume_403_unassigned_sub_admin(client):
    """Sub-admin cannot tailor a submission not assigned to them."""
    super_headers, _ = _create_super_admin(client)
    sub_headers, _ = _create_sub_admin(client)
    sub_id = _create_submission(client)
    _save_resume(client, super_headers, sub_id)

    resp = client.post(
        f"/api/v1/admin/submissions/{sub_id}/tailor",
        headers=sub_headers,
        json={"provider": "openai"},
    )
    assert resp.status_code == 403
    assert "not assigned" in resp.json()["detail"]["message"].lower()


def test_tailor_resume_401_unauthenticated(client):
    """Unauthenticated request returns 401."""
    sub_id = _create_submission(client)
    resp = client.post(
        f"/api/v1/admin/submissions/{sub_id}/tailor",
        json={"provider": "openai"},
    )
    assert resp.status_code == 401


def test_tailor_resume_503_no_api_keys(client):
    """Returns 503 when no LLM API keys are configured."""
    super_headers, _ = _create_super_admin(client)
    sub_id = _create_submission(client)
    _save_resume(client, super_headers, sub_id)

    with patch(
        "app.services.ai_service.call_llm_provider",
        new_callable=AsyncMock,
        side_effect=Exception(
            "No AI provider API key is configured. "
            "Please add OPENAI_API_KEY or GEMINI_API_KEY to your environment variables."
        ),
    ):
        resp = client.post(
            f"/api/v1/admin/submissions/{sub_id}/tailor",
            headers=super_headers,
            json={"provider": "openai"},
        )
    assert resp.status_code == 503


def test_tailor_resume_500_llm_error(client):
    """Returns 500 on unexpected LLM failure."""
    super_headers, _ = _create_super_admin(client)
    sub_id = _create_submission(client)
    _save_resume(client, super_headers, sub_id)

    with patch(
        "app.services.ai_service.call_llm_provider",
        new_callable=AsyncMock,
        side_effect=Exception("OpenAI API Error (500): Internal server error"),
    ):
        resp = client.post(
            f"/api/v1/admin/submissions/{sub_id}/tailor",
            headers=super_headers,
            json={"provider": "openai"},
        )
    assert resp.status_code == 500


@_mock_tailor
def test_tailor_resume_with_custom_instructions(client):
    """Custom instructions are accepted and tailor still succeeds."""
    super_headers, _ = _create_super_admin(client)
    sub_id = _create_submission(client)
    _save_resume(client, super_headers, sub_id)

    resp = client.post(
        f"/api/v1/admin/submissions/{sub_id}/tailor",
        headers=super_headers,
        json={
            "provider": "openai",
            "model": "gpt-4o",
            "custom_instructions": "Emphasise the 40% latency reduction metric strongly.",
            "include_chat_history": True,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status_code"] == 201
    assert len(resp.json()["data"]["documents"]) == 4


@_mock_tailor
def test_tailor_resume_prompt_usage_count_incremented(client):
    """Tailoring increments the usage_count on the selected prompt template."""
    super_headers, _ = _create_super_admin(client)
    sub_id = _create_submission(client)
    _save_resume(client, super_headers, sub_id)

    # Get baseline usage count
    prompts_before = client.get(
        "/api/v1/admin/prompts", headers=super_headers
    ).json()["data"]["prompts"]
    # Tech submission → Software Engineer CV prompt
    swe_prompt = next(p for p in prompts_before if p["category"] == "Technology")
    before_count = swe_prompt["usage_count"]

    client.post(
        f"/api/v1/admin/submissions/{sub_id}/tailor",
        headers=super_headers,
        json={"provider": "openai"},
    )

    prompts_after = client.get(
        "/api/v1/admin/prompts", headers=super_headers
    ).json()["data"]["prompts"]
    swe_after = next(p for p in prompts_after if p["category"] == "Technology")
    assert swe_after["usage_count"] == before_count + 1
