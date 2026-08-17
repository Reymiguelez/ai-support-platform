from datetime import datetime
from email.message import EmailMessage

import aiosmtplib

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str | None = None,
) -> bool:
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP not configured, skipping email", to=to_email)
        return False

    message = EmailMessage()
    message["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    message["To"] = to_email
    message["Subject"] = subject

    message.set_content(text_content or html_content)
    message.add_alternative(html_content, subtype="html")

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=settings.SMTP_TLS,
        )
        logger.info("Email sent successfully", to=to_email, subject=subject)
        return True
    except Exception as e:
        logger.error("Failed to send email", to=to_email, error=str(e))
        return False


async def send_email_verification(email: str, token: str) -> bool:
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .button {{ display: inline-block; padding: 12px 24px; background-color: #2563eb; color: white; text-decoration: none; border-radius: 6px; font-weight: 600; }}
            .footer {{ margin-top: 24px; padding-top: 24px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Verify Your Email Address</h1>
            <p>Welcome to {settings.PROJECT_NAME}! Please click the button below to verify your email address.</p>
            <p style="text-align: center; margin: 32px 0;">
                <a href="{verification_url}" class="button">Verify Email</a>
            </p>
            <p>Or copy this link: {verification_url}</p>
            <p>This link expires in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS} hours.</p>
            <div class="footer">
                <p>If you didn't create an account, you can safely ignore this email.</p>
                <p>&copy; {datetime.now().year} {settings.PROJECT_NAME}. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_content = f"""
    Verify Your Email Address

    Welcome to {settings.PROJECT_NAME}! Please visit the following link to verify your email address:

    {verification_url}

    This link expires in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS} hours.

    If you didn't create an account, you can safely ignore this email.
    """

    return await send_email(
        email, f"Verify your email - {settings.PROJECT_NAME}", html_content, text_content
    )


async def send_password_reset_email(email: str, token: str) -> bool:
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .button {{ display: inline-block; padding: 12px 24px; background-color: #dc2626; color: white; text-decoration: none; border-radius: 6px; font-weight: 600; }}
            .footer {{ margin-top: 24px; padding-top: 24px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Reset Your Password</h1>
            <p>You requested a password reset for your {settings.PROJECT_NAME} account. Click the button below to create a new password.</p>
            <p style="text-align: center; margin: 32px 0;">
                <a href="{reset_url}" class="button">Reset Password</a>
            </p>
            <p>Or copy this link: {reset_url}</p>
            <p>This link expires in {settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS} hour(s).</p>
            <div class="footer">
                <p>If you didn't request a password reset, you can safely ignore this email.</p>
                <p>&copy; {datetime.now().year} {settings.PROJECT_NAME}. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_content = f"""
    Reset Your Password

    You requested a password reset for your {settings.PROJECT_NAME} account. Visit the following link to create a new password:

    {reset_url}

    This link expires in {settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS} hour(s).

    If you didn't request a password reset, you can safely ignore this email.
    """

    return await send_email(
        email, f"Reset your password - {settings.PROJECT_NAME}", html_content, text_content
    )
