"""
Tests for GET /api/v1/admin/ai/models

Covers:
- Returns 200 with a list of models and source field
- Returns curated fallback list when no OpenAI key is configured
- Returns 'openai_api' source when OpenAI API responds successfully (mocked)
- Returns curated fallback when OpenAI API returns non-200 (mocked)
- Returns curated fallback when OpenAI API call times out / raises (mocked)
- Each model entry contains required fields: id, label, tier, note
- 401 for unauthenticated requests
- Sub-admin can also call this endpoint (not restricted to super admin)
"""

from unittest.mock import AsyncMock, MagicMock, patch


# ── helpers ───────────────────────────────────────────────────────────────────

def _create_and_login(client, email, role="super_admin"):
    client.post("/api/v1/admin/auth/create-admin", json={
        "first_name": "Models", "last_name": "Tester",
        "email": email, "password": "Password123!", "role": role,
    })
    resp = client.post("/api/v1/admin/auth/login",
                       json={"email": email, "password": "Password123!"})
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


MOCK_OPENAI_MODELS_RESPONSE = {
    "data": [
        {"id": "gpt-4o",          "object": "model"},
        {"id": "gpt-4o-mini",     "object": "model"},
        {"id": "gpt-4-turbo",     "object": "model"},
        {"id": "gpt-3.5-turbo",   "object": "model"},
        # These should be filtered out
        {"id": "whisper-1",       "object": "model"},
        {"id": "dall-e-3",        "object": "model"},
        {"id": "text-embedding-3-small", "object": "model"},
    ]
}


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_ai_models_returns_200(client):
    """Endpoint returns 200 for an authenticated admin."""
    headers = _create_and_login(client, "models.super@example.com")
    resp = client.get("/api/v1/admin/ai/models", headers=headers)
    assert resp.status_code == 200


def test_ai_models_response_shape(client):
    """Response has status, message, and data with models list + source."""
    headers = _create_and_login(client, "models.shape@example.com")
    resp = client.get("/api/v1/admin/ai/models", headers=headers)
    body = resp.json()
    assert body["status"] == "success"
    assert "data" in body
    assert "models" in body["data"]
    assert "source" in body["data"]
    assert isinstance(body["data"]["models"], list)
    assert len(body["data"]["models"]) > 0


def test_ai_models_each_entry_has_required_fields(client):
    """Every model entry must have id, label, tier, note."""
    headers = _create_and_login(client, "models.fields@example.com")
    resp = client.get("/api/v1/admin/ai/models", headers=headers)
    models = resp.json()["data"]["models"]
    for model in models:
        assert "id" in model, f"Missing 'id' in: {model}"
        assert "label" in model, f"Missing 'label' in: {model}"
        assert "tier" in model, f"Missing 'tier' in: {model}"
        assert "note" in model, f"Missing 'note' in: {model}"


def test_ai_models_curated_fallback_when_no_key(client):
    """When OPENAI_API_KEY is not set, returns curated list with source='curated'."""
    headers = _create_and_login(client, "models.nokey@example.com")

    with patch("app.services.ai_service.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = None
        mock_settings.GEMINI_API_KEY = None
        resp = client.get("/api/v1/admin/ai/models", headers=headers)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["source"] == "curated"
    assert len(data["models"]) > 0


def test_ai_models_from_openai_api_when_key_available(client):
    """When key is present and OpenAI responds 200, source='openai_api' and chat models returned."""
    headers = _create_and_login(client, "models.liveapi@example.com")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_OPENAI_MODELS_RESPONSE

    with patch("app.services.ai_service.settings") as mock_settings, \
         patch("httpx.AsyncClient") as mock_httpx:
        mock_settings.OPENAI_API_KEY = "sk-fake-key-for-testing"
        mock_settings.GEMINI_API_KEY = None

        # async with httpx.AsyncClient() as client: client.get(...)
        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)
        mock_async_client.get = AsyncMock(return_value=mock_resp)
        mock_httpx.return_value = mock_async_client

        resp = client.get("/api/v1/admin/ai/models", headers=headers)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["source"] == "openai_api"

    # Whisper, dall-e, embedding models should be filtered out
    model_ids = [m["id"] for m in data["models"]]
    assert "whisper-1" not in model_ids
    assert "dall-e-3" not in model_ids
    assert "text-embedding-3-small" not in model_ids

    # Chat models should be present
    assert any(m.startswith("gpt-") for m in model_ids)


def test_ai_models_curated_fallback_on_openai_api_error(client):
    """Falls back to curated list when OpenAI returns a non-200 status."""
    headers = _create_and_login(client, "models.apierr@example.com")

    mock_resp = MagicMock()
    mock_resp.status_code = 401  # Unauthorized from OpenAI

    with patch("app.services.ai_service.settings") as mock_settings, \
         patch("httpx.AsyncClient") as mock_httpx:
        mock_settings.OPENAI_API_KEY = "sk-bad-key"
        mock_settings.GEMINI_API_KEY = None

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)
        mock_async_client.get = AsyncMock(return_value=mock_resp)
        mock_httpx.return_value = mock_async_client

        resp = client.get("/api/v1/admin/ai/models", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["data"]["source"] == "curated"


def test_ai_models_curated_fallback_on_network_exception(client):
    """Falls back to curated list when the network call raises an exception."""
    headers = _create_and_login(client, "models.netfail@example.com")

    with patch("app.services.ai_service.settings") as mock_settings, \
         patch("httpx.AsyncClient") as mock_httpx:
        mock_settings.OPENAI_API_KEY = "sk-any-key"
        mock_settings.GEMINI_API_KEY = None

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)
        mock_async_client.get = AsyncMock(
            side_effect=Exception("Network timeout")
        )
        mock_httpx.return_value = mock_async_client

        resp = client.get("/api/v1/admin/ai/models", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["data"]["source"] == "curated"


def test_ai_models_sub_admin_can_access(client):
    """Sub-admin is NOT restricted from this endpoint."""
    headers = _create_and_login(client, "models.sub@example.com", role="sub_admin")
    resp = client.get("/api/v1/admin/ai/models", headers=headers)
    assert resp.status_code == 200


def test_ai_models_401_unauthenticated(client):
    """Unauthenticated request returns 401."""
    resp = client.get("/api/v1/admin/ai/models")
    assert resp.status_code == 401


def test_ai_models_curated_contains_gpt4o(client):
    """The curated fallback list must include gpt-4o as a top recommendation."""
    headers = _create_and_login(client, "models.gpt4o@example.com")

    with patch("app.services.ai_service.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = None
        mock_settings.GEMINI_API_KEY = None
        resp = client.get("/api/v1/admin/ai/models", headers=headers)

    models = resp.json()["data"]["models"]
    gpt4o = next((m for m in models if m["id"] == "gpt-4o"), None)
    assert gpt4o is not None
    assert gpt4o["tier"] == "recommended"
