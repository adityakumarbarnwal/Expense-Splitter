"""
Email service using aiosmtplib.

Sends emails for:
- Group membership invitations
- Password reset OTPs

Gracefully handles failures — email failure does NOT roll back database state,
except for OTP emails where the caller cleans up on failure.

SMTP timeout: 15 seconds per connection — prevents indefinite blocking.
"""
import logging
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Bounded SMTP timeout — prevents indefinite blocking on slow/dead SMTP servers
_SMTP_TIMEOUT_SECONDS = 15


async def send_group_invitation_email(
    to_email: str,
    to_name: str,
    group_name: str,
    inviter_name: str,
) -> bool:
    """
    Send a group invitation email.

    Returns True on success, False on failure.
    Failure is logged but does NOT raise — caller handles it gracefully.
    """
    if not settings.mail_enabled:
        logger.info(
            "Email disabled. Would have sent group invitation to %s for group '%s'",
            to_email, group_name,
        )
        return True  # Pretend success in dev

    subject = f"You've been added to '{group_name}' on SplitIt"
    app_link = f"{settings.frontend_url}/groups"

    html_body = f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 24px;">
      <h2 style="color: #6366f1;">You've been added to a group!</h2>
      <p>Hi <strong>{to_name}</strong>,</p>
      <p><strong>{inviter_name}</strong> has added you to the group
         <strong>"{group_name}"</strong> on SplitIt.</p>
      <p>You can now view shared expenses, balances, and settlements for this group.</p>
      <p style="margin-top: 24px;">
        <a href="{app_link}"
           style="background: #6366f1; color: white; padding: 12px 24px;
                  border-radius: 6px; text-decoration: none; font-weight: bold;">
          View Group
        </a>
      </p>
      <hr style="margin-top: 32px; border: none; border-top: 1px solid #e5e7eb;" />
      <p style="color: #9ca3af; font-size: 12px;">
        SplitIt — Group Expense Splitter
      </p>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.mail_from_name} <{settings.mail_from}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.mail_server,
            port=settings.mail_port,
            username=settings.mail_username or None,
            password=settings.mail_password or None,
            start_tls=settings.mail_starttls,
            timeout=_SMTP_TIMEOUT_SECONDS,
        )
        logger.info("Group invitation email sent to %s", to_email)
        return True
    except Exception as e:
        logger.error("Failed to send invitation email to %s: %s", to_email, e)
        return False


async def send_password_reset_otp_email(
    to_email: str,
    to_name: str,
    otp: str,
) -> bool:
    """
    Send a password reset OTP email.

    Returns True on success, False on failure.
    Failure is logged but does NOT raise — caller handles it gracefully.

    IMPORTANT: When mail_enabled=False this function returns False (not True),
    so the caller (forgot_password endpoint) will NOT leave a usable OTP in
    the database. The endpoint already guards against calling this function
    when mail is disabled, but this is a defence-in-depth measure.
    """
    if not settings.mail_enabled:
        logger.warning(
            "MAIL_ENABLED=False — OTP email NOT sent to %s. "
            "Configure SMTP and set MAIL_ENABLED=true to enable password reset.",
            to_email,
        )
        return False  # Caller will delete the OTP document on False

    subject = "Your Password Reset OTP — SplitIt"
    html_body = f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 24px;">
      <h2 style="color: #6366f1;">Password Reset Request</h2>
      <p>Hi <strong>{to_name}</strong>,</p>
      <p>We received a request to reset your password for SplitIt.</p>
      <p>Your 6-digit verification code is:</p>
      <div style="background: #f3f4f6; border-radius: 8px; padding: 16px; text-align: center; margin: 24px 0;">
        <span style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #1f2937;">{otp}</span>
      </div>
      <p>This code will expire in <strong>10 minutes</strong>. If you did not request this code, you can safely ignore this email.</p>
      <hr style="margin-top: 32px; border: none; border-top: 1px solid #e5e7eb;" />
      <p style="color: #9ca3af; font-size: 12px;">
        SplitIt — Group Expense Splitter
      </p>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.mail_from_name} <{settings.mail_from}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.mail_server,
            port=settings.mail_port,
            username=settings.mail_username or None,
            password=settings.mail_password or None,
            start_tls=settings.mail_starttls,
            timeout=_SMTP_TIMEOUT_SECONDS,
        )
        logger.info("Password reset OTP email sent to %s", to_email)
        return True
    except Exception as e:
        logger.error("Failed to send password reset OTP email to %s: %s", to_email, e)
        return False
