import resend
import os
from jinja2 import Environment, FileSystemLoader
from app.utils.settings import settings
from datetime import date, datetime, timezone

EMAIL_CRED = settings.RESEND_EMAIL

base_dir = settings.BASE_DIR
template_dir = os.path.join(base_dir, "app", "templates", "emails")
env = Environment(loader=FileSystemLoader(template_dir))
resend.api_key = settings.RESEND_API_KEY


async def send_reset_password_email(
    to_email: str,
    first_name: str,
    role: str,
    reset_link: str,
    expires_at: datetime,
) -> bool:
    """
    Send a magic-link password reset email to an admin or sub-admin.

    Returns True on success, False on failure (caller decides how to handle).
    """
    try:
        template = env.get_template("reset_password.html")

        # Format role for display: "super_admin" -> "Super Admin"
        role_display = role.replace("_", " ").title()

        # Format expiry time as a readable UTC string.
        # Always normalise to UTC before formatting so the displayed time
        # matches the actual JWT expiry regardless of server timezone.
        if expires_at:
            utc_expires = expires_at.astimezone(timezone.utc)
            expires_at_str = utc_expires.strftime("%B %d, %Y at %I:%M %p UTC")
        else:
            expires_at_str = "30 minutes from now"

        html_body = template.render(
            first_name=first_name,
            role=role_display,
            reset_link=reset_link,
            expires_at=expires_at_str,
            year=date.today().year,
        )

        params: resend.Emails.SendParams = {
            "from": EMAIL_CRED,
            "to": [to_email],
            "subject": "Reset Your MangoHR Password",
            "html": html_body,
        }

        resend.Emails.send(params)
        return True

    except Exception as e:
        print(f"[email_services] Failed to send reset password email to {to_email}: {e}")
        return False
