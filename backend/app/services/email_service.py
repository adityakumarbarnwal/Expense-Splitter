"""
Email service using aiosmtplib.

Sends emails for:
- Group membership invitations

Gracefully handles failures — email failure does NOT roll back database state.
"""
import logging
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


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

    subject = f"You've been added to '{group_name}' on Group Expense Splitter"
    app_link = f"{settings.frontend_url}/groups"

    html_body = f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 24px;">
      <h2 style="color: #2563eb;">You've been added to a group!</h2>
      <p>Hi <strong>{to_name}</strong>,</p>
      <p><strong>{inviter_name}</strong> has added you to the group
         <strong>"{group_name}"</strong> on Group Expense Splitter.</p>
      <p>You can now view shared expenses, balances, and settlements for this group.</p>
      <p style="margin-top: 24px;">
        <a href="{app_link}"
           style="background: #2563eb; color: white; padding: 12px 24px;
                  border-radius: 6px; text-decoration: none; font-weight: bold;">
          View Group
        </a>
      </p>
      <hr style="margin-top: 32px; border: none; border-top: 1px solid #e5e7eb;" />
      <p style="color: #9ca3af; font-size: 12px;">
        Group Expense Splitter — DSC4141 Academic Project
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
    """
    if not settings.mail_enabled:
        logger.info(
            "Email disabled. Would have sent OTP to %s",
            to_email,
        )
        return True  # Pretend success in dev

    subject = "Your Password Reset OTP — Group Expense Splitter"
    html_body = f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 24px;">
      <h2 style="color: #2563eb;">Password Reset Request</h2>
      <p>Hi <strong>{to_name}</strong>,</p>
      <p>We received a request to reset your password for Group Expense Splitter.</p>
      <p>Your 6-digit verification code is:</p>
      <div style="background: #f3f4f6; border-radius: 8px; padding: 16px; text-align: center; margin: 24px 0;">
        <span style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #1f2937;">{otp}</span>
      </div>
      <p>This code will expire in <strong>10 minutes</strong>. If you did not request this code, you can safely ignore this email.</p>
      <hr style="margin-top: 32px; border: none; border-top: 1px solid #e5e7eb;" />
      <p style="color: #9ca3af; font-size: 12px;">
        Group Expense Splitter — DSC4141 Academic Project
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
        )
        logger.info("Password reset OTP email sent to %s", to_email)
        return True
    except Exception as e:
        logger.error("Failed to send password reset OTP email to %s: %s", to_email, e)
        return False

