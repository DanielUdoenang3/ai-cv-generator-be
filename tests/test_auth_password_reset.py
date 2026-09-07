"""
Tests for:
  POST /api/v1/admin/auth/forgot-password
  POST /api/v1/admin/auth/reset-password

Covers:
- forgot-password always returns 200 (prevents email enumeration)
- forgot-password sets reset_token + reset_token_expires_at on the admin record
- reset-password with valid token resets password and returns access_token
- reset-password with invalid token returns 400
- reset-password with expired token returns 400
- reset-password token is single-use (second use returns 400)
- new password is immediately usable for login
- old password no longer works after reset
- forgot-password for non-existent email returns generic 200 (no leak)
- forgot-password for inactive admin returns generic 200
- forgot-password sends email (mocked) without error
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest


# ── helpers ───────────────────────────────────────────────────────────────────

def _create_admin(client, email, role="super_admin",
                  first_name="Reset", last_name="User", password="OldPassword123!"):
    resp = client.post("/api/v1/admin/auth/create-admin", json={
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "password": password,
        "role": role,
    })
    assert resp.status_code in [200, 201]
    return resp.json()["data"]


def _get_reset_token(client, email, db_session):
    """
    Trigger forgot-password and read the token directly from the DB.
    Email is mocked to prevent real SMTP calls.
    """
    with patch(
        "app.services.admin.auth.send_reset_password_email",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = client.post("/api/v1/admin/auth/forgot-password",
                           json={"email": email})
    assert resp.status_code == 200

    from app.models.admins import Admin
    admin = db_session.query(Admin).filter(Admin.email == email).first()
    assert admin.reset_token is not None
    return admin.reset_token


# ── forgot-password tests ─────────────────────────────────────────────────────

def test_forgot_password_returns_200_for_known_email(client):
    """Always returns 200 with generic message for a registered super_admin."""
    _create_admin(client, "fp.known@example.com", role="super_admin")

    with patch("app.services.admin.auth.send_reset_password_email",
               new_callable=AsyncMock, return_value=None):
        resp = client.post("/api/v1/admin/auth/forgot-password",
                           json={"email": "fp.known@example.com"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert "reset link" in body["message"].lower()


def test_forgot_password_returns_200_for_unknown_email(client):
    """Returns the same generic 200 for an email that doesn't exist (no enumeration)."""
    resp = client.post("/api/v1/admin/auth/forgot-password",
                       json={"email": "nobody@example.com"})
    assert resp.status_code == 200
    assert "reset link" in resp.json()["message"].lower()


def test_forgot_password_persists_token_in_db(client, db_session):
    """After request, reset_token and reset_token_expires_at are set on the admin."""
    _create_admin(client, "fp.token@example.com", role="super_admin")

    with patch("app.services.admin.auth.send_reset_password_email",
               new_callable=AsyncMock, return_value=None):
        client.post("/api/v1/admin/auth/forgot-password",
                    json={"email": "fp.token@example.com"})

    from app.models.admins import Admin
    admin = db_session.query(Admin).filter(Admin.email == "fp.token@example.com").first()
    assert admin.reset_token is not None
    assert admin.reset_token_expires_at is not None
    # Token should expire roughly 30 min from now
    expiry = admin.reset_token_expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    assert expiry > now
    assert expiry < now + timedelta(minutes=35)


def test_forgot_password_sub_admin_eligible(client):
    """sub_admin is also eligible for the magic-link flow."""
    _create_admin(client, "fp.sub@example.com", role="sub_admin")

    with patch("app.services.admin.auth.send_reset_password_email",
               new_callable=AsyncMock, return_value=None):
        resp = client.post("/api/v1/admin/auth/forgot-password",
                           json={"email": "fp.sub@example.com"})
    assert resp.status_code == 200


def test_forgot_password_inactive_admin_generic_response(client, db_session):
    """An inactive admin gets the same generic 200 (no leak of account status)."""
    _create_admin(client, "fp.inactive@example.com", role="super_admin")

    # Deactivate the admin directly in DB
    from app.models.admins import Admin
    admin = db_session.query(Admin).filter(Admin.email == "fp.inactive@example.com").first()
    admin.is_active = False
    db_session.commit()

    resp = client.post("/api/v1/admin/auth/forgot-password",
                       json={"email": "fp.inactive@example.com"})
    assert resp.status_code == 200
    assert "reset link" in resp.json()["message"].lower()


# ── reset-password tests ──────────────────────────────────────────────────────

def test_reset_password_success_returns_access_token(client, db_session):
    """Valid token → password updated, fresh access_token returned."""
    _create_admin(client, "rp.success@example.com", role="super_admin")
    token = _get_reset_token(client, "rp.success@example.com", db_session)

    resp = client.post("/api/v1/admin/auth/reset-password", json={
        "token": token,
        "new_password": "BrandNewPassword456!",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert "access_token" in body["data"]
    assert body["data"]["email"] == "rp.success@example.com"


def test_reset_password_new_password_works_for_login(client, db_session):
    """After reset, the new password can be used to log in."""
    _create_admin(client, "rp.login@example.com",
                  role="super_admin", password="OldPass123!")
    token = _get_reset_token(client, "rp.login@example.com", db_session)

    client.post("/api/v1/admin/auth/reset-password", json={
        "token": token,
        "new_password": "NewSecurePass789!",
    })

    login_resp = client.post("/api/v1/admin/auth/login", json={
        "email": "rp.login@example.com",
        "password": "NewSecurePass789!",
    })
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()["data"]


def test_reset_password_old_password_rejected_after_reset(client, db_session):
    """After reset, the old password no longer works."""
    _create_admin(client, "rp.old@example.com",
                  role="super_admin", password="OldPass123!")
    token = _get_reset_token(client, "rp.old@example.com", db_session)

    client.post("/api/v1/admin/auth/reset-password", json={
        "token": token,
        "new_password": "NewSecurePass789!",
    })

    # Old password should now fail
    old_resp = client.post("/api/v1/admin/auth/login", json={
        "email": "rp.old@example.com",
        "password": "OldPass123!",
    })
    assert old_resp.status_code == 401


def test_reset_password_token_cleared_after_use(client, db_session):
    """After successful reset, reset_token is cleared in the DB (single-use)."""
    _create_admin(client, "rp.clear@example.com", role="super_admin")
    token = _get_reset_token(client, "rp.clear@example.com", db_session)

    client.post("/api/v1/admin/auth/reset-password", json={
        "token": token,
        "new_password": "ClearedToken999!",
    })

    from app.models.admins import Admin
    db_session.expire_all()
    admin = db_session.query(Admin).filter(Admin.email == "rp.clear@example.com").first()
    assert admin.reset_token is None
    assert admin.reset_token_expires_at is None


def test_reset_password_token_is_single_use(client, db_session):
    """Using the same token twice returns 400 on the second attempt."""
    _create_admin(client, "rp.single@example.com", role="super_admin")
    token = _get_reset_token(client, "rp.single@example.com", db_session)

    # First use — succeeds
    r1 = client.post("/api/v1/admin/auth/reset-password", json={
        "token": token, "new_password": "FirstReset123!",
    })
    assert r1.status_code == 200

    # Second use — should fail (token was cleared)
    r2 = client.post("/api/v1/admin/auth/reset-password", json={
        "token": token, "new_password": "SecondReset456!",
    })
    assert r2.status_code == 400
    assert "already been used" in r2.json()["detail"]["message"].lower() or \
           "invalid" in r2.json()["detail"]["message"].lower() or \
           "expired" in r2.json()["detail"]["message"].lower()


def test_reset_password_invalid_token_returns_400(client):
    """Completely bogus token returns 400."""
    resp = client.post("/api/v1/admin/auth/reset-password", json={
        "token": "this.is.not.a.real.jwt",
        "new_password": "SomePassword123!",
    })
    assert resp.status_code == 400
    assert "invalid" in resp.json()["detail"]["message"].lower() or \
           "expired" in resp.json()["detail"]["message"].lower()


def test_reset_password_expired_token_returns_400(client, db_session):
    """A token whose DB expiry is in the past returns 400."""
    _create_admin(client, "rp.expired@example.com", role="super_admin")
    token = _get_reset_token(client, "rp.expired@example.com", db_session)

    # Backdate the expiry to the past
    from app.models.admins import Admin
    admin = db_session.query(Admin).filter(Admin.email == "rp.expired@example.com").first()
    admin.reset_token_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()

    resp = client.post("/api/v1/admin/auth/reset-password", json={
        "token": token,
        "new_password": "ExpiredToken999!",
    })
    assert resp.status_code == 400
    assert "expired" in resp.json()["detail"]["message"].lower()


def test_reset_password_422_missing_fields(client):
    """Omitting required fields returns 422."""
    resp = client.post("/api/v1/admin/auth/reset-password", json={})
    assert resp.status_code == 422


def test_forgot_password_422_invalid_email_format(client):
    """Sending a malformed email returns 422 from schema validation."""
    resp = client.post("/api/v1/admin/auth/forgot-password",
                       json={"email": "not-an-email"})
    assert resp.status_code == 422
